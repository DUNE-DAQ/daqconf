"""HW: Uniqueness enforcer for DAQ configuration objects.

This module provides utilities to detect DAL (Data Abstraction Layer) objects
that share the same class and id across multiple configuration files, report
on conflicts, and offer strategies to rename conflicting objects to enforce
uniqueness.

Main responsibilities:
- Scan a folder of oks configuration files and collect DAL definitions.
- Compare DALs with the same class/id across files for attribute and
    relationship equality.
- Produce human-friendly reports (console tables and CSV) describing
    uniqueness violations.
- Offer pluggable renaming schemes to resolve conflicts automatically or
    with user input.

The behaviour intentionally does not modify files unless the caller
commits changes via the provided `ConfigLoader.commit_changes` interface.
"""

from typing import Any, List, Dict, Set, Tuple, Optional, Type
from pathlib import Path
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import warnings

from rich.table import Table
from rich.console import Console
from rich.prompt import Prompt

from conffwk import Configuration

# ------ Errors -------#
class RenamedDalError(Exception): ...


class SchemeNotFoundError(Exception):
    def __init__(self, scheme_name, scheme_list):
        message = f"Error could not find {scheme_name} in {scheme_list}"
        super().__init__(message)

class EndNameGenerationEarly(Exception):
    ...

# ------ Helper Classes ------ #
# Helper functions to convert DAL to unique key and back
class DALKeyConverter:
    """Convert a DAL object to a string key and back.

    DAL objects are not safely hashable, so the converter produces a
    stable string key of the form ``<ClassName>@<id>`` which can be used in
    sets and dictionaries for comparison purposes.
    """

    DELIMITER = "@"

    @staticmethod
    def dal_to_key(dal) -> str:
        """Return a stable string key for the given DAL.

        The produced string looks like ``ClassName@id`` and is used as a
        dictionary/set key when comparing DALs across configurations.
        """
        return f"{dal.className()}{DALKeyConverter.DELIMITER}{dal.id}"

    @staticmethod
    def key_to_dal(key: str) -> Tuple[str, str]:
        """Split a key previously produced by :meth:`dal_to_key`.

        Returns a tuple ``(className, id)``.
        """
        dal_class, dal_id = key.split(DALKeyConverter.DELIMITER)
        return dal_class, dal_id


# ------ Uniqueness Enforcement Classes ------ #


@dataclass
class UniquenessInformant:
    """Container for information about a single uniqueness violation.

    Instances capture whether attributes and relationships match between
    definitions, which configuration/session files are involved, and the
    proposed/assigned names when renaming is applied.
    """

    dal_id: str
    dal_class: str
    relationships_match: bool = True
    attributes_match: bool = True
    conflicted_sessions: list[str] = field(default_factory=lambda: [])
    contained_in_files: list[Path] = field(default_factory=lambda: [])
    session_files: list[Path] = field(default_factory=lambda: [])
    names: list[str] = field(default_factory=lambda: [])

    def as_table(self) -> Table:
        # If there are no conflicts, return an informative empty table
        if not self.conflicted_sessions:
            return Table(
                title=f"No uniqueness violations for {self.dal_class}, {self.dal_id}"
            )

        table = Table(
            title=f"Uniqueness Violation for [bold red]{self.dal_class}, {self.dal_id}"
        )

        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Status / Details", style="magenta")

        rels_status = (
            "[green]Match[/green]"
            if self.relationships_match
            else "[red]Do Not Match[/red]"
        )
        attrs_status = (
            "[green]Match[/green]"
            if self.attributes_match
            else "[red]Do Not Match[/red]"
        )

        table.add_row("Relationships", rels_status)
        table.add_row("Attributes", attrs_status)

        # Existing summary rows
        sessions = ", ".join(self.conflicted_sessions)
        table.add_row("Conflicted Sessions", sessions)

        session_files = ", ".join(str(f.name) for f in self.session_files)
        table.add_row("Session Files", session_files)

        contained_in = ", ".join(str(f.name) for f in self.contained_in_files)
        table.add_row("Contained In Files", contained_in)

        if self.names:
            names = ", ".join(self.names)
            table.add_row("DAL Names", names)

        table.add_row("Renaming Info", "")
        for file, session, new_name in zip(
            self.contained_in_files, self.conflicted_sessions, self.names
        ):
            table.add_row(
                f"• {file.name}",
                f"Session: {session}\nRenamed to: [bold]{new_name}[/bold]",
            )

        return table

    def to_csv_row(self) -> str:
        """
        Convert the uniqueness violation to a CSV row
        """
        sessions = ";".join(self.conflicted_sessions)
        contained_in = ";".join(str(f.name) for f in self.contained_in_files)
        session_files = ";".join(str(f.name) for f in self.session_files)
        names = ";".join(self.names)
        return f'{self.dal_class},{self.dal_id},{self.relationships_match},{self.attributes_match},"{sessions}","{session_files}","{names}","{contained_in}"\n'


class UniquenessInformantGroup:
    """Collection of :class:`UniquenessInformant` objects with helpers.

    Provides an operation to merge entries that refer to the same DAL
    (same class and id) so reporting and renaming operate on a single
    canonical entry per conflict.
    """

    def __init__(self, enforcers: List[UniquenessInformant]):
        self.enforcers = enforcers

    def add_enforcer(self, enforcer: UniquenessInformant):
        self.enforcers.append(enforcer)

    def get_enforcers(self) -> List[UniquenessInformant]:
        return self.enforcers

    def combine_identical_objects(self):
        """Merge enforcers referring to the same (class, id) pair.

        When duplicates are found the properties are combined conservatively:
        - relationships_match and attributes_match are ANDed together
        - lists of sessions, files and proposed names are concatenated so
            subsequent processing can assign or select per-file names.
        """
        combined: Dict[Tuple[str, str], UniquenessInformant] = {}

        for enforcer in self.enforcers:
            key = (enforcer.dal_class, enforcer.dal_id)
            if key not in combined:
                combined[key] = enforcer
            else:
                existing = combined[key]
                existing.relationships_match &= enforcer.relationships_match
                existing.attributes_match &= enforcer.attributes_match
                existing.conflicted_sessions.extend(enforcer.conflicted_sessions)
                existing.contained_in_files.extend(enforcer.contained_in_files)
                existing.session_files.extend(enforcer.session_files)
                existing.names.extend(enforcer.names)

        self.enforcers = list(combined.values())


class UniquenessReportPrinter:
    """
    Class to print and export uniqueness reports
    """

    def __init__(self, enforcers: UniquenessInformantGroup):
        self.enforcers = enforcers

    def print_report(self):
        console = Console()
        if not self.enforcers:
            console.print("No uniqueness violations found!", style="bold green")
            return

        for enforcer in self.enforcers.get_enforcers():
            console.print(enforcer.as_table())

    def to_csv(self) -> str:
        """
        Convert the report to CSV format
        """
        header = "DAL Class,DAL ID,Relationships Match,Attributes Match,Conflicted Sessions,Session Files,New Names,Contained In Files\n"
        rows = [enforcer.to_csv_row() for enforcer in self.enforcers.get_enforcers()]
        return header + "".join(rows)

    def __call__(self, output_csv: Optional[Path] = None):
        self.print_report()
        if output_csv:
            csv_content = self.to_csv()
            with open(output_csv, "w") as f:
                f.write(csv_content)


# ---- Name generation ----
class DalNameGeneratorBase(ABC):
    def __init__(self, dal, config: Configuration):
        self.dal = dal
        self.config = config
        self._name = None

    @property
    def name(self) -> str:
        if self._name is None:
            self._name = self.generate_name()
        return self._name

    def find_related_dal(self):
        """
        Finds the DAL that includes this DAL in its relationships
        """
        all_dals = list(self.config.get_all_dals().values())

        for candidate in all_dals:
            relations = self.config.relations(candidate.className(), all=True)
            for rel in relations:
                related = getattr(candidate, rel, [])
                if not isinstance(related, list):
                    related = [related]
                if self.dal in related:
                    return candidate
        return None

    @abstractmethod
    def generate_name(self) -> str: ...

    def rename(self):
        self.dal.rename(self.name)
        self.config.update_dal(self.dal)

    @classmethod
    @abstractmethod
    def help_message(cls) -> str: ...


class EnforceredNameGenerator(DalNameGeneratorBase):
    """
    Generate a unique name for a DAL based on its enforcer information
    """

    def __init__(self, dal, config: Configuration, enforcer: UniquenessInformantGroup):
        super().__init__(dal, config)

        if hasattr(dal, "__old_id") and dal.id != dal.__old_id:
            raise ValueError(
                f"DAL {dal.className()}, {dal.id} has already been renamed from {dal.__old_id}, cannot rename again."
            )

        self.enforcer = enforcer
        self.enforcer = enforcer

        self._enforced = self.dal_in_enforcer(dal)

        if self._enforced is None:
            raise ValueError(
                f"DAL {dal.className()}, {dal.id} not found in enforcer list."
            )

        if dal.id in self._enforced.names:
            raise RenamedDalError(
                f"DAL {dal.className()}, {dal.id} already has a name assigned in enforcer."
            )

        # We an find the current name index based on the contained_in file
        contained_in = self.config.get_obj(dal.className(), dal.id).contained_in()
        try:
            self.name_index = self._enforced.contained_in_files.index(
                Path(contained_in)
            )
        except ValueError:
            raise ValueError(
                f"DAL {dal.className()}, {dal.id} contained in file {contained_in} not found in enforcer's contained_in_files."
            )

    def dal_in_enforcer(self, dal_obj) -> Optional[UniquenessInformant]:
        for info in self.enforcer.get_enforcers():
            if (
                info.dal_id == dal_obj.id or dal_obj.id in info.names
            ) and info.dal_class == dal_obj.className():
                return info

        return None


class InheritedNameGenerator(EnforceredNameGenerator):
    """
    Generate a unique name for a DAL based on its class and id
    """

    def generate_name(self) -> str:
        related_dal = self.find_related_dal()
        if not related_dal:
            return f"{self.dal.id}"

        return f"{related_dal.id}_{self.dal.id}"

    @classmethod
    def help_message(cls) -> str:
        return "For any objects with duplicates changes the name to {containing object}_{dal_id}."


class GroupNameGenerator(EnforceredNameGenerator):
    """
    Generate a unique name for Groups DALs
    """

    def __camel_to_initials(self, name: str) -> str:
        initials = "".join([char for char in name if char.isupper()])
        return initials.lower()

    def generate_name(self) -> str:
        related_dal = self.find_related_dal()
        if not related_dal:
            return f"{self.dal.id}"

        # Find the relationship that links to this Group
        relations = self.config.relations(related_dal.className(), all=True)

        related = []
        for rel in relations:
            related = getattr(related_dal, rel, [])
            if not isinstance(related, list):
                related = [related]
            if self.dal in related:
                break
        else:
            warnings.warn(
                f"Could not find relationship linking {related_dal.className()}, {related_dal.id} to {self.dal.className()}, {self.dal.id}."
            )
            return f"{self.dal.id}"

        # We now process ALL related DALs in this relationship to build the name
        name_base_str = f"{related_dal.id}"

        for n, dal in enumerate(related):
            name = self._add_to_name_map(n, name_base_str, dal)
            if dal.id == self.dal.id:
                self._name = name

        return self._name

    def _add_to_name_map(self, idx: int, name_base_str: str, dal):
        # Convert
        dal_class = self.__camel_to_initials(dal.className())
        name = f"{name_base_str}_{dal_class}_{idx}"

        dal_enforcer_instance = self.dal_in_enforcer(dal)

        if dal_enforcer_instance is None:
            # We generated a name for a DAL that is not in the enforcer list, so we add a new entry
            new_info = UniquenessInformant(
                dal_id=dal.id, dal_class=dal.className(), names=[name]
            )

            dal_file = self.config.get_obj(dal.className(), dal.id).contained_in()
            new_info.contained_in_files.append(Path(dal_file))

            self.enforcer.add_enforcer(new_info)
        else:
            contained_in = self.config.get_obj(dal.className(), dal.id).contained_in()

            # We now find the index of this file in the enforcer's contained_in_files to assign the name correctly
            try:
                file_index = dal_enforcer_instance.contained_in_files.index(
                    Path(contained_in)
                )
                dal_enforcer_instance.names[file_index] = name
            except Exception as _:
                # File not found, we append
                dal_enforcer_instance.contained_in_files.append(Path(contained_in))
                dal_enforcer_instance.session_files.append(
                    self._enforced.session_files[self.name_index]
                )
                dal_enforcer_instance.names.append(name)
        return name

    @classmethod
    def help_message(cls) -> str:
        return "Groups items together if they are part of the same relationship. Naming convention is {top level object}_{class initials}_{i}\n\
            For example foo_1000, foo_1200, foo_1020 of class FooObject stored in foo_storage would become foo_storage_fo_0, foo_storage_fo_1, foo_storage_fo_2."


class PromptNameGenerator(EnforceredNameGenerator):
    """
    Generate a unique name for a DAL based on user input
    """

    def generate_name(self) -> str:
        console = Console()
        related_dal = self.find_related_dal()

        console.print(
            f"Renaming DAL [bold]{self.dal.className()}, {self.dal.id}[/bold] found in file [bold]{self.config.get_obj(self.dal.className(), self.dal.id).contained_in()}[/bold]."
        )
        if related_dal:
            console.print(
                f"Object is referenced by: [bold]{related_dal.className()}, {related_dal.id}[/bold]."
            )

        while True:
            prompt_msg = f"Enter new name for [bold green]{self.dal.id}[/bold green]: "
            new_name = Prompt.ask(prompt_msg)

            # Check if user is sure
            confirm = Prompt.ask(
                f"Confirm renaming [bold]{self.dal.className()}, {self.dal.id}[/bold] to [bold]{new_name}[/bold]? (y/n/q)",
                choices=["y", "n", "q"],
                default="y",
            )
            if confirm.lower() == "y":
                return new_name
            elif confirm.lower()=="n":
                console.print(
                    "Renaming cancelled by user, please try again.", style="bold red"
                )                
            else:
                prompt_msg = Prompt.ask("Are you sure you want to quit? (y/n)", choices=['y','n'], default='n')
                if prompt_msg == 'y':            
                    raise EndNameGenerationEarly()
                

    @classmethod
    def help_message(cls) -> str:
        return "Manually create names for each item in the configuration"


# ----- Renaming Engines ------ #
class RenameEngine:
    """Apply a chosen renaming scheme to a set of uniqueness informants.

    The engine keeps a small cache of opened `Configuration` objects to
    avoid reloading the same session files multiple times.
    """

    _SCHEMES: Dict[str, Type[EnforceredNameGenerator]] = {
        "inherit": InheritedNameGenerator,
        "group": GroupNameGenerator,
        "prompt": PromptNameGenerator,
    }

    _CONFIG_CACHE = {}

    def recognised_schemes(self):
        """Return the list of recognised renaming scheme names.

        These names correspond to keys in ``_SCHEMES`` and can be passed to
        :meth:`apply_scheme` or displayed to the user.
        """
        return list(self._SCHEMES.keys())

    def get_help_message(self, scheme: str):
        if scheme not in self.recognised_schemes():
            raise SchemeNotFoundError(scheme, self.recognised_schemes())
        return self._SCHEMES[scheme].help_message()

    def get_scheme(self, scheme: str, dal, config, enforcers):
        """Instantiate the named renaming scheme for a particular DAL.

        Raises :class:`ValueError` if the scheme is not recognised.
        """
        if scheme not in self.recognised_schemes():
            raise ValueError(f"Renaming scheme {scheme} not recgonised. ")

        return self._SCHEMES[scheme](dal, config, enforcers)

    def apply_scheme(self, scheme: str, enforcers: UniquenessInformantGroup):
        """Apply a renaming scheme to all enforcers.

        For each enforcer we iterate the session files that contained the
        conflicting DAL and open the corresponding `Configuration` (cached).
        A generator for the selected scheme is created and invoked to rename
        the DAL. Any errors are reported to the console but do not stop the
        overall process.
        """
        if scheme not in self.recognised_schemes():
            raise SchemeNotFoundError(scheme, self.recognised_schemes())

        for enforcer in enforcers.get_enforcers():
            user_end = False
            
            for config_name in enforcer.session_files:
                # Reuse a cached configuration object when possible
                config = self._CONFIG_CACHE.get(config_name, None)

                if config is None:
                    self._CONFIG_CACHE[config_name] = config = Configuration(
                        f"oksconflibs:{config_name}"
                    )

                dal = config.get_dal(enforcer.dal_class, enforcer.dal_id)
                try:
                    # Instantiate and run the renaming generator
                    generator = self.get_scheme(scheme, dal, config, enforcers)  # type: ignore [we check this earlier!]
                    generator.rename()
                    enforcer.names.append(generator.name)
                except RenamedDalError:
                    # Already renamed elsewhere; skip silently
                    continue
                
                except EndNameGenerationEarly:
                    Console().print("[bold red]END EARLY![/]")
                    user_end = True
                    break
                
                except Exception as e:
                    console = Console()
                    console.print(
                        f"[bold red]Failed to rename DAL {dal.className()}, {dal.id} in config {config_name}:[/bold red] {e}"
                    )
            
            # if ended early!
            if user_end:
                break

        # After renaming, combine entries again so names and file lists are
        # updated consistently for reporting.
        enforcers.combine_identical_objects()
        
    def commit_changes(self):
        for config in self._CONFIG_CACHE.values():
            config.commit()


# ------ Config and DAL operations ------ #


class ConfigLoader:
    """Load and inspect oks configuration files from a folder.

    The loader collects all DALs and exposes methods to detect DALs that are
    defined in more than one configuration and to produce
    :class:`UniquenessInformantGroup` reports describing conflicts.
    """

    def __init__(self, config_folder: Path):
        """Initialise loader and pre-load configurations.

        `config_folder` must be a directory containing oks ``*.data.xml``
        files. The constructor also records session names for easy user
        facing reporting.
        """
        if not config_folder.is_dir():
            raise ValueError(f"Provided path {config_folder} is not a directory.")
        self.configs = self.load_configs(config_folder)

        self._session_names = {c: c.get_dals("Session")[0].id for c in self.configs}

        self.dals = self.collect_dals()
        self._renamer = RenameEngine()

    def load_configs(self, config_folder: Path) -> List[Configuration]:
        """Load all oks `*.data.xml` files in the folder as `Configuration` objects.

        Returns a list of `Configuration` instances.
        """
        configs = [
            Configuration(f"oksconflibs:{f}") for f in config_folder.glob("*.data.xml")
        ]
        return configs

    def collect_dals(self) -> Dict[str, List[Configuration]]:
        """Return a mapping of DAL key -> list of configurations containing it.

        Keys are produced by :class:`DALKeyConverter` and are stable across
        configurations to allow grouping by (class, id).
        """
        dal_map: Dict[str, List[Configuration]] = {}
        for config in self.configs:
            dals = config.get_all_dals()
            for dal in dals.values():
                unique_key = DALKeyConverter.dal_to_key(dal)

                if unique_key not in dal_map:
                    dal_map[unique_key] = []
                dal_map[unique_key].append(config)
        return dal_map

    def dal_uniquely_defined(
        self, dal_class_id_key: str, configs: List[Configuration]
    ) -> UniquenessInformant:
        """Create a :class:`UniquenessInformant` for a specific DAL key.

        Compares the definitions found in ``configs`` and records whether
        attributes and relationships match. If the same DAL instance is
        defined in multiple files (i.e. contained_in differs) the conflict
        is recorded for reporting/renaming.
        """
        dal_class, dal_id = DALKeyConverter.key_to_dal(dal_class_id_key)

        enforcer = UniquenessInformant(dal_id=dal_id, dal_class=dal_class)

        if len(configs) <= 1:
            return enforcer  # No conflict

        init_dal = configs[0].get_dal(dal_class, dal_id)
        contained_in_init = self.__get_contained_in(init_dal, configs[0])

        for config in configs[1:]:
            compare_dal = config.get_dal(dal_class, dal_id)
            contained_in_compare = self.__get_contained_in(compare_dal, config)

            in_multiple_files = contained_in_init != contained_in_compare

            if not in_multiple_files:
                continue  # Same file, no conflict

            comparison = DalComparison(init_dal, compare_dal, configs[0])
            rels_match, attrs_match = comparison()

            if not rels_match:
                enforcer.relationships_match = False
            if not attrs_match:
                enforcer.attributes_match = False

            enforcer.conflicted_sessions.append(self._session_names[config])
            enforcer.session_files.append(Path(config.databases[0]))
            enforcer.contained_in_files.append(
                self.__get_contained_in(compare_dal, config)
            )

        # If there are conflicts, add the first session as well for reference
        if enforcer.conflicted_sessions:
            enforcer.conflicted_sessions.insert(0, self._session_names[configs[0]])
            enforcer.session_files.insert(0, Path(configs[0].databases[0]))
            enforcer.contained_in_files.insert(
                0, self.__get_contained_in(init_dal, configs[0])
            )
        return enforcer

    def __get_contained_in(self, dal, config) -> Path:
        """Return the path of the file that contains the given DAL.

        The underlying `Configuration` API provides a ``contained_in`` method
        on objects; wrap it and return a :class:`Path` for convenience.
        """
        obj = config.get_obj(dal.className(), dal.id)
        return Path(obj.contained_in())

    def check_dal_uniqueness(self) -> UniquenessInformantGroup:
        """Walk the collected DALs and return a group of conflicts found.

        Only DALs with actual conflicts (i.e. defined in multiple files and
        differing in attributes or relationships) are included in the result.
        """
        results: UniquenessInformantGroup = UniquenessInformantGroup([])

        for dal_key, configs in self.dals.items():
            enforcer = self.dal_uniquely_defined(dal_key, configs)
            if enforcer.conflicted_sessions:
                results.add_enforcer(enforcer)

        return results

    def __call__(self) -> UniquenessInformantGroup:
        # Generate the enforcers and optionally prompt the user to rename
        # conflicted DALs. Return the enforcer group for further action.
        enforcer = self.check_dal_uniqueness()

        if (
            Prompt.ask(
                "Do you want to rename conflicting DALs to enforce uniqueness? (y/n)",
                choices=["y", "n"],
                default="n",
            )
            == "n"
        ):
            return enforcer

        
        choices = self._renamer.recognised_schemes() + ["help"]

        while True:
            rename = Prompt.ask(
                f"Enter renaming scheme ({','.join(c for c in choices)}):",
                choices=choices,
                default="help",
                case_sensitive=False,
            ).lower()
            
            # just to be sure!            
            if rename in choices[:-1]:
                break

            if rename != "help":
                Console().print(f"{rename} not recognised")

            self._display_help(self._renamer)

        if rename:
            self._renamer.apply_scheme(rename, enforcer)
        return enforcer

    def _display_help(self, rename_engine: RenameEngine):
        console = Console()
        console.print("[bold]Renaming Schemes:[/bold]")
        for choice in rename_engine.recognised_schemes():
            console.print(
                f" - [bold green]{choice}[/bold green] [cyan]{rename_engine.get_help_message(choice)}[/]"
            )

        console.print(
            " - [bold green]help[/bold green]: [cyan]Display this message.[/]"
        )

    def commit_changes(self):
        """
        Commit any changes made to the configurations
        """
        for config in self.configs:
            # print(f"Updating {config}")
            config.commit("update")
        
        # Also rename here 
        self._renamer.commit_changes()        
    


class DalComparison:
    def __init__(self, dal_1, dal_2, reference_config: Configuration):
        """Compare two DAL objects for equality of attributes and
        relationships using a provided reference configuration for schema
        information (attributes/relations lists).
        """
        self.dal_1 = dal_1
        self.dal_2 = dal_2
        self.reference_config = reference_config

    def compare_attributes(self) -> bool:
        """Return True if all attribute values are equal on both DALs.

        The attribute names are obtained from the reference configuration
        based on the class name of ``dal_1``.
        """
        attrs = self.reference_config.attributes(self.dal_1.className())

        for attr in attrs:
            val1 = getattr(self.dal_1, attr)
            val2 = getattr(self.dal_2, attr)
            if val1 != val2:
                return False
        return True

    def compare_relationships(self) -> bool:
        """Return True if all relationship sets are equal between the two DALs.

        Relationships are compared as sets of DAL keys produced by the
        :class:`DALKeyConverter` so ordering differences do not affect the
        result.
        """
        rels = self.reference_config.relations(self.dal_1.className(), all=True)

        for rel in rels:
            rels_1 = self.__rels_to_ids(self.dal_1, rel)
            rels_2 = self.__rels_to_ids(self.dal_2, rel)

            if rels_1 != rels_2:
                return False

        return True

    def __rels_to_ids(self, dal, rel_name: str) -> Set[str]:
        """Return a set of DAL keys corresponding to related objects.

        Handles single-object relationships (non-list) and None values by
        normalising them to a list or empty set respectively.
        """
        related_dals = getattr(dal, rel_name, [])

        if related_dals is None:
            return set()

        if not isinstance(related_dals, list):
            related_dals = [related_dals]
        return set([DALKeyConverter.dal_to_key(r) for r in related_dals])

    def __call__(self) -> Any:
        rels_equal = self.compare_relationships()
        attrs_equal = self.compare_attributes()
        return rels_equal, attrs_equal


# Front end interface
class UniquenessEnforcerContextManager:
    def __init__(self, config_folder: Path, output_csv: Optional[Path] = None):
        self.config_folder = config_folder
        self.output_csv = output_csv

        self._loader = ConfigLoader(self.config_folder)
        self._reporter = None

    def commit(self):
        if self._reporter is None:
            raise RuntimeError("No report generated yet, cannot commit changes.")

        if (
            Prompt.ask(
                "Do you want to commit the changes to the configuration files? (y/n)",
                choices=["y", "n"],
                default="n",
            ) == "y"
        ):
            if not self.output_csv:
                Console().print(
                    "[bold yellow] Warning: No output CSV specified. In order to track the changes we will generate a csv to uniqueness_report.csv .[/bold yellow]"
                )
                self.output_csv = Path("uniqueness_report.csv")

            self._loader.commit_changes()

    def __call__(self):
        enforcers = self._loader()
        self._reporter = UniquenessReportPrinter(enforcers)
        self._reporter(self.output_csv)
        self.commit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        Console().print("Exiting Uniqueness Enforcer.")
        if exc_type is KeyboardInterrupt:
            try:
                self.commit()
            except Exception as e:
                Console().print(f"[bold red]Failed to commit changes:[/bold red] {e}")
                return False

        return True

if __name__ == "__main__":
    '''
    main stuff here for debugging!
    '''
    from pathlib import Path
    import sys
    if len(sys.argv) < 2:
        print("Usage: python uniqueness_enforcer.py <config_folder> [output_csv]")
        sys.exit(1)

    config_folder = Path(sys.argv[1])
    output_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    with UniquenessEnforcerContextManager(config_folder, output_csv) as enforcer:
        enforcer()