"""
HW: Finds non-unique DAL objects and provides a simple CLI to rename them iteratively
"""
from typing import Dict, List, Set
from collections import defaultdict
from pathlib import Path
from itertools import combinations
import re

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from rich.panel import Panel
import click

from conffwk import Configuration
from conffwk.dal import DalBase

console = Console()


# ----- Errors -----

class ConfigCommitError(Exception):
    def __init__(self, config) -> None:
        super().__init__(f"Cannot commit changes to {config}, make sure it isn't open in another process!")


# ----- Relationship Cache -----

class RelationshipCache:
    """Caches parent-child relationships between DAL objects to avoid repeated DB calls."""

    def __init__(self, db: Configuration | str):
        if isinstance(db, str):
            db = Configuration("oksconflibs:" + db)
        self.db = db
        self._relations_cache: Dict[str, List[str]] = {}
        self._parents_cache: Dict[DalBase, List[DalBase]] = {}
        self.graph = self._build_graph()

    def _relations(self, class_name: str) -> List[str]:
        if class_name not in self._relations_cache:
            self._relations_cache[class_name] = self.db.relations(class_name, all=True)
        return self._relations_cache[class_name]

    def _build_graph(self) -> Dict[DalBase, List[DalBase]]:
        graph = {}
        for obj in self.db.get_all_dals().values():
            children = []
            for rel in self._relations(obj.className()):
                related = getattr(obj, rel, None)
                if related is None:
                    continue
                children.extend(related if isinstance(related, list) else [related])
            if children:
                graph[obj] = children
        return graph

    def get_parents(self, obj: DalBase) -> List[DalBase]:
        if obj not in self._parents_cache:
            self._parents_cache[obj] = [
                parent for parent, children in self.graph.items() if obj in children
            ]
        return self._parents_cache[obj]


# ----- Extended DAL (wraps a DAL with its config + tree context) -----

class ExtendedDal:
    """A DAL object enriched with its configuration and relationship tree."""

    def __init__(self, dal: DalBase, config: Configuration, tree: RelationshipCache):
        self.dal = dal
        self.config = config
        self.tree = tree
        self._attributes: Dict[str, object] | None = None
        self._relations: Dict[str, Set[str]] | None = None

    @property
    def id(self) -> str:
        return self.dal.id

    @property
    def attributes(self) -> Dict[str, object]:
        if self._attributes is None:
            self._attributes = {
                a: getattr(self.dal, a, None)
                for a in self.config.attributes(self.dal.className())
            }
        return self._attributes

    @property
    def relations(self) -> Dict[str, Set[str]]:
        if self._relations is None:
            self._relations = {}
            for rel in self.config.relations(self.dal.className(), all=True):
                related = getattr(self.dal, rel, None)
                if related is None:
                    related = []
                elif not isinstance(related, list):
                    related = [related]
                self._relations[rel] = {repr(r) for r in related}
        return self._relations

    def get_parents(self) -> List[DalBase]:
        return self.tree.get_parents(self.dal)

    def rename(self, name: str) -> None:
        self.dal.rename(name)
        self.config.update_dal(self.dal)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExtendedDal):
            return False
        return (
            self.dal.className() == other.dal.className()
            and self.id == other.id
            and self.attributes == other.attributes
            and self.relations == other.relations
        )

    def has_same_parents(self, other: "ExtendedDal") -> bool:
        return self.get_parents() == other.get_parents()


# ----- Consolidated group of duplicate DALs -----

class DalGroup:
    """A deduplicated group of DAL objects that share the same repr (i.e. are duplicates)."""

    def __init__(self, pairs: List[tuple], trees: Dict[Configuration, RelationshipCache]):
        seen: List[ExtendedDal] = []
        for dal, config in pairs:
            ext = ExtendedDal(dal, config, trees[config])
            if not any(ext == existing for existing in seen):
                seen.append(ext)
        self.members = seen

    @property
    def dals(self) -> List[DalBase]:
        return [m.dal for m in self.members]

    @property
    def has_same_parents(self) -> bool:
        return any(a.has_same_parents(b) for a, b in combinations(self.members, 2))

    def __len__(self) -> int:
        return len(self.members)

    def __getitem__(self, idx: int) -> ExtendedDal:
        return self.members[idx]

    def __iter__(self):
        return iter(self.members)


# ----- Tree-based sorting -----

def _natural_sort_key(s: str) -> list:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", s)]


def sort_groups_by_depth(
    groups: List[DalGroup],
    trees: Dict[Configuration, RelationshipCache],
) -> List[DalGroup]:
    """Sort DalGroups by their depth in the configuration tree (BFS from Session root)."""
    all_ids = {g.dals[0].id for g in groups}
    tree_list = list(trees.values())
    covered: Set[str] = set()
    sorted_groups: List[DalGroup] = []
    iteration = 0

    while covered != all_ids:
        iteration += 1

        if iteration == 1:
            sessions = tree_list[0].db.get_dals("Session")
            if not sessions:
                raise ValueError("Configuration must contain a Session object!")
            root = sessions[0]
        else:
            remaining = all_ids - covered
            root = next((g.dals[0] for g in groups if g.dals[0].id in remaining), None)
            if root is None:
                break

        # BFS to build depth map
        depth_map: Dict[str, int] = {}
        queue = [(root, 0)]
        visited: Set[int] = set()

        while queue:
            obj, depth = queue.pop(0)
            if id(obj) in visited:
                continue
            visited.add(id(obj))
            depth_map[obj.id] = depth
            covered.add(obj.id)

            seen_children: Set[int] = set()
            for tree in tree_list:
                for child in tree.graph.get(obj, []):
                    if id(child) not in visited and id(child) not in seen_children:
                        queue.append((child, depth + 1))
                        seen_children.add(id(child))

        batch = [g for g in groups if g.dals[0].id in depth_map]
        batch.sort(key=lambda g: (depth_map[g.dals[0].id], _natural_sort_key(g.dals[0].id)))
        sorted_groups.extend(batch)

    return sorted_groups


# ----- DAL Collector -----

class DalCollector:
    """Loads all configurations and finds duplicate DAL objects across them."""

    def __init__(self, configs: List[Configuration]):
        self.configs = configs

        console.print("[blue]Building configuration trees…[/]")
        self.trees = {c: RelationshipCache(c) for c in configs}

        # Group all (dal, config) pairs by DAL repr
        grouped: Dict[str, List[tuple]] = defaultdict(list)
        for config in configs:
            for dal in config.get_all_dals().values():
                grouped[repr(dal)].append((dal, config))

        # Keep only groups with more than one unique member
        groups = [DalGroup(pairs, self.trees) for pairs in grouped.values()]
        self.groups = [g for g in groups if len(g) > 1]

        if self.groups:
            self.groups = sort_groups_by_depth(self.groups, self.trees)

    def commit(self):
        for config in self.configs:
            config.commit()

    def __len__(self) -> int:
        return len(self.groups)

    def __getitem__(self, idx: int) -> DalGroup:
        return self.groups[idx]


# ----- CLI -----

class RenameDalCli:
    def __init__(self, collector: DalCollector):
        self.collector = collector
        self.history: list = []
        self._idx = 0

    def run(self):
        groups = self.collector.groups
        if not groups:
            console.print("[green]No duplicate DALs found.[/]")
            return

        last = "n"
        # Rich treats [...] as markup tags, so use \[ to render literal square brackets
        prompt = r"\[n] next, \[p] prev, \[c] commit, \[s] save & quit, \[q] quit, or a number to rename"

        while self._idx <= len(groups):
            # End-of-list: offer save/back/quit instead of silently exiting
            if self._idx == len(groups):
                console.print("\n[bold]Reached the end of all duplicate groups.[/]")
                action = Prompt.ask(
                    r"\[s] save & quit, \[p] go back, \[q] quit without saving",
                    default="s",
                ).lower().strip()
                if action == "p":
                    self._idx -= 1
                elif action == "s":
                    self.collector.commit()
                    console.print("[bold green]Saved and exiting.[/]")
                    return
                else:
                    console.print("[bold red]Exiting without saving.[/]")
                    return
                continue

            group = groups[self._idx]
            self._render(group)
            console.print(f"[dim]({self._idx + 1}/{len(groups)})[/]")

            action = Prompt.ask(prompt, default=last).lower().strip()

            if action == "n":
                self._idx += 1
                last = action
            elif action == "p":
                if self._idx > 0:
                    self._idx -= 1
                else:
                    console.print("[yellow]Already at the first item.[/]")
                last = action
            elif action == "c":
                self.collector.commit()
                console.print("[bold green]Changes committed.[/]")
            elif action == "s":
                self.collector.commit()
                console.print("[bold green]Saved and exiting.[/]")
                return
            elif action == "q":
                console.print("[bold red]Exiting without saving.[/]")
                return
            elif action.isdigit():
                self._handle_rename(action, group)
                last = action
            else:
                console.print("[red]Unknown command.[/]")

    def _render(self, group: DalGroup):
        console.clear()

        if group.has_same_parents:
            console.print(
                Panel(
                    "[bold red]Renaming Disabled[/]\n\n"
                    "These duplicate DALs share the same parents.\n"
                    "Renaming would cause commit inconsistencies.",
                    title="⚠ WARNING",
                    border_style="red",
                    expand=False,
                )
            )
            console.print()

        table = Table(title="Duplicated DAL Objects")
        for col, style in [("#", ""), ("DAL ID", "cyan"), ("Class", "magenta"),
                           ("Configuration", "purple"), ("Parents", "blue"),
                           ("Attributes", "green"), ("Relations", "yellow")]:
            table.add_column(col, style=style, justify="right" if col == "#" else "left")

        for i, ext in enumerate(group, 1):
            attr_str = ", ".join(f"{k}={v}" for k, v in ext.attributes.items())
            rel_str = ", ".join(f"{k}=[{', '.join(v)}]" for k, v in ext.relations.items())
            table.add_row(
                str(i), ext.id, ext.dal.className(),
                str(ext.config), str(ext.get_parents()),
                attr_str, rel_str,
            )

        console.print(table)

    def _handle_rename(self, action: str, group: DalGroup):
        if group.has_same_parents:
            console.print("[bold red]Renaming disabled — these DALs share the same parents.[/]")
            Prompt.ask("[dim]Press Enter to continue[/]", default="")
            return

        idx = int(action) - 1
        if not (0 <= idx < len(group)):
            console.print("[red]Invalid number.[/]")
            Prompt.ask("[dim]Press Enter to continue[/]", default="")
            return

        ext = group[idx]
        console.print(f"Renaming [cyan]{ext.id}[/] ({ext.dal.className()})")
        new_name = Prompt.ask("Enter new name (or empty to cancel)").strip()
        if not new_name:
            console.print("[yellow]Rename cancelled.[/]")
            return

        old_name = ext.id
        ext.rename(new_name)
        self.history.append((ext, old_name))
        console.print(f"[green]Renamed {old_name} → {new_name}[/]")


@click.command()
@click.option("--input-folder", "-i", required=True, type=click.Path())
def rename_duplicate_dals(input_folder: str):
    folder = Path(input_folder)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Cannot find {folder}")

    configs = [Configuration(f"oksconflibs:{f}") for f in folder.glob("*.data.xml")]
    if not configs:
        raise FileNotFoundError(
            "No configs found — ensure the folder contains .data.xml files."
        )

    collector = DalCollector(configs)
    RenameDalCli(collector).run()


if __name__ == "__main__":
    rename_duplicate_dals()