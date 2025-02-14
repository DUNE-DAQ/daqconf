"""
NOT COMPLETE!
"""

from textual import on
from textual.widgets import Select, Button, Static, Label
from textual.widgets import Button
from textual.containers import VerticalScroll
from rich.console import RichCast, ConsoleRenderable

from typing import Any

from daqconf.cider.widgets.configuration_controller import ConfigurationController
from daqconf.cider.widgets.custom_rich_log import RichLogWError



class SingleRelationshipModifier(Static):
    def __init__(self, relationship_type: str, current_related_dal: Any, relationship_name: str,
                 renderable: ConsoleRenderable | RichCast | str = "", *, expand: bool = False,
                 shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None,
                 classes: str | None = None, disabled: bool = False) -> None:

        super().__init__(renderable, expand=expand, shrink=shrink, markup=markup,
                         name=name, id=id, classes=classes, disabled=disabled)

        self._relationship_type = relationship_type
        self._current_related_dal = current_related_dal
        self._relationship_name = relationship_name

    @property
    def current_dal(self):
        return self._current_related_dal

    def compose(self):
        # Need to get the main screen etc.
        main_screen = self.app.get_screen("main")
        self._config_controller: ConfigurationController = main_screen.query_one(ConfigurationController)
        self._logger:  RichLogWError = main_screen.query_one("#main_log")

        # yield Grid(
            # Actual dropdown menu
        yield Select([(repr(rel), rel) for 
                        rel in self._config_controller.get_dals_of_class(self._relationship_type)],
                value=self._current_related_dal, id="select_obj")
            # Need a delete button
        yield Button("Delete", id="delete_rel", variant="error")
        
        
    @on(Select.Changed)
    def select_changed(self, event: Select.Changed)->None:
        # Want to update the DAL
        # HACK I really hate this, currently select can't deal with complex types
        # Rather than change the low down stuff we convert to dal here
        self._current_related_dal = event.value
        try:
            self._config_controller.modify_current_dal_relationship(self._relationship_name, self._current_related_dal)
        except Exception as e:
            self._logger.write_error(e)
            
    
    @on(Button.Pressed)
    def button_pressed(self, event: Button.Pressed)->None:
        if event.button.id=="delete_rel":
            # Pop dal [if it's empty will just delete]
            try:            
                self._config_controller.pop_dal_relationship(self._relationship_name, self._current_related_dal)
            except:
                self._logger.write("[bold blue]Info:[/bold blue] [blue]Removing duplicate")
            self.remove()
            

class RelationshipTypeGroup(Static):
    def __init__(self, relationship_name: str, renderable: ConsoleRenderable | RichCast | str = "", *, expand: bool = False, shrink: bool = False, markup: bool = True, name: str | None = None, id: str | None = None, classes: str | None = None, disabled: bool = False) -> None:
        super().__init__(renderable, expand=expand, shrink=shrink, markup=markup, name=name, id=id, classes=classes, disabled=disabled)    

        self._relationship_name = relationship_name

    def compose(self):
        main_screen = self.app.get_screen("main")
        self._config_controller: ConfigurationController = main_screen.query_one(ConfigurationController)
        self._logger:  RichLogWError = main_screen.query_one("#main_log")

        # Grab relations
        relationship_dict = self._config_controller.get_relation_category_in_current_dal(self._relationship_name)
        
        self._rinfo = relationship_dict['rel_info']
        rel_list = relationship_dict[self._relationship_name]
        
        # Want to be able to grab these
        # self._dropdown_list = [SingleRelationshipModifier(self._rinfo["type"], r, self._relationship_name) ]
        
        self._dropdown_list = [SingleRelationshipModifier(self._rinfo["type"], r, self._relationship_name) for r in rel_list]
         
        yield Label(self._relationship_name)
        for s in self._dropdown_list:
            yield s

        # logic for button being disabled
        add_deactivated = (not self._rinfo['multivalue'] \
                            and len(self._dropdown_list)>1 \
                            or len(self._dropdown_list)==len(self._config_controller.get_dals_of_class(self._rinfo['type'])))
            

        yield Button("Add Relation", "success", id="add_dal", disabled=add_deactivated)

    def verify_unique_dals(self):
        # Dumb hack, since dals occasionally have hache issues, replaces with string representation
        selected_dals = [repr(s.current_dal) for s in self._dropdown_list]
        
        # Which lets us convert the entire thing to a set
        if len(selected_dals)!=len(set(selected_dals)):
            raise Exception(f"Error DAL list contains non-unique entry for {self._relationship_name}")

        # If this is meant to be implemented, has it been?
        if len(selected_dals)==0 and self._rinfo['not-null']:
            raise Exception(f"Error {self._relationship_name} is required but has no DALs...")
    
    def _add_new_selection_box(self):
        if not len(self._config_controller.get_dals_of_class(self._rinfo["type"])):
            raise Exception(f"Error cannot find any objects of type {self._rinfo['type']}")
        
        s = SingleRelationshipModifier(self._rinfo["type"], 
                                       self._config_controller.get_dals_of_class(self._rinfo["type"])[0]
                                       , self._relationship_name)
        self._dropdown_list.append(s)
        self.mount(s)
    
    @on(Button.Pressed)
    def button_pressed(self, event: Button.Pressed):
        if event.button.id !="add_dal":
            return
        
        self._add_new_selection_box()

class RelationshipSelectPanel(Static):
    def compose(self):
        main_screen = self.app.get_screen("main")
        self._config_controller: ConfigurationController = main_screen.query_one(ConfigurationController)
        self._logger:  RichLogWError = main_screen.query_one("#main_log")

        relation_names = [list(r.keys())[0] for r in self._config_controller.get_relations_to_current_dal()]

        self._relation_groups = [RelationshipTypeGroup(r) for r in relation_names]

        yield VerticalScroll(
            *self._relation_groups,
            id="rel_groups_vert"
        )
        
    def verify_relations(self):
        for r in self._relation_groups:
            try:
                r.verify_unique_dals()
            except Exception as e:
                self._logger.write(e)


