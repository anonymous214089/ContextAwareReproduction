class State():
    def __init__(self, state_id: str, activity: str):
        self.state_id = state_id
        self.activity = activity.split(".")[-1]
        self.views_in_state = {}
        self.path_to_state = []

    def add_view(self, view_key, view_info):
        if view_key not in self.views_in_state.keys():
            self.views_in_state.setdefault(view_key, view_info)

    def set_path_to_state(self, view_path):
        if len(self.path_to_state) == 0:
            self.path_to_state = view_path

    def has_edittext(self):
        for view_key, view in self.views_in_state.items():
            if view.view_class[-8:].lower() == "edittext":
                return True
        return False

    def get_all_edittext(self):
        state_edittext = []
        for view_key, view in self.views_in_state.items():
            if view.view_class[-8:].lower() == "edittext":
                state_edittext.append(view_key)
        return state_edittext