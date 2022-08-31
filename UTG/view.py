import re

class View():
    def __init__(self, view_info: dict):
        # default properties
        self.img_path = ""
        self.view_class = ""
        self.view_type = ""
        self.clickable = ""
        self.long_clickable = ""
        self.bounds = [[0, 0], [0, 0]]
        self.text = ""
        self.content_desc = ""
        self.hint = ""
        self.resource_id = ""
        self.abs_location = ""
        self.src_state = ""
        self.xpath = ""
        # infer properties
        self.neighbor_text = ""
        self.sibling_text = []
        self.process_sibling_text = ""
        self.child_text = []
        self.process_child_text = ""
        self.parent_text = ""
        self.dst_state = ""
        self.dst_state_not_sure = False

        # do init by info type
        if view_info["format"] == "droidbot":
            self.init_by_droidbot(view_info)
        else:
            pass


    def init_by_droidbot(self, view_info: dict):
        self.img_path = view_info["img_path"]
        self.view_class = view_info["class"]
        self.view_type = view_info["type"]
        self.clickable = view_info["clickable"]
        self.bounds = view_info["bounds"]
        self.text = view_info["text"]
        self.content_desc = view_info["content_desc"]
        self.hint = "none"
        self.resource_id = view_info["resource_id"]
        self.abs_location = self.get_obj_abs_location(view_info["bounds"])
        self.src_state = view_info["src_state"]
        self.xpath = view_info["xpath"]
        self.neighbor_text = view_info["neighbor_text"]
        self.sibling_text = view_info["sibling_text"]
        self.process_sibling_text = view_info["process_sibling_text"]
        self.child_text = view_info["child_text"]
        self.process_child_text = view_info["process_child_text"]
        self.parent_text = view_info["parent_text"]
        self.dst_state = view_info["dst_state"]
        self.dst_state_not_sure = view_info["dst_state_not_sure"]

    def get_obj_abs_location(self, bounds):
        abs_location = [["top left corner", "top", "top right corner"], ["left", "center", "right"],
                        ["bottom left corner", "bottom", "bottom right corner"]]
        posx = (bounds[0][0] + bounds[1][0]) / 2
        posy = (bounds[0][1] + bounds[1][1]) / 2
        width_idx = int((3 * posx) // 1080)
        height_idx = int((3 * posy) // 1920)
        return abs_location[height_idx][width_idx]

    def __str__(self):
        view_tokens = []
        view_tokens.extend(["[type]", self.view_type])
        view_tokens.extend(["[text]", self.text])
        view_tokens.extend(["[content_desc]", self.content_desc])
        view_tokens.extend(["[hint]", self.hint])
        view_tokens.extend(["[resource_id]", self.resource_id])
        view_tokens.extend(["[abs_location]", self.abs_location])
        view_tokens.extend(["[neighbor_text]", self.neighbor_text])
        view_tokens.extend(["[sibling_text]", self.process_sibling_text])
        view_tokens.extend(["[child_text]", self.process_child_text])
        view_tokens.extend(["[parent_text]", self.parent_text])
        view_str = " ".join(view_tokens)
        view_str = re.sub(r"\s+", " ", view_str).strip()

        trans_str = self.src_state + " -> " + self.dst_state
        all_str = trans_str + "\n" + view_str
        return view_str
        # return all_str

    def to_dict(self):
        all_info = {}
        all_info.setdefault("img_path", self.img_path)
        all_info.setdefault("class", self.view_class)
        all_info.setdefault("type", self.view_type)
        all_info.setdefault("clickable", self.clickable)
        all_info.setdefault("long_clickable", self.long_clickable)
        all_info.setdefault("bounds", self.bounds.copy())
        all_info.setdefault("text", self.text)
        all_info.setdefault("content_desc", self.content_desc)
        all_info.setdefault("hint", self.hint)
        all_info.setdefault("resource_id", self.resource_id)
        all_info.setdefault("abs_location", self.abs_location)
        all_info.setdefault("src_state", self.src_state)
        all_info.setdefault("xpath", self.xpath)
        all_info.setdefault("neighbor_text", self.neighbor_text)
        all_info.setdefault("sibling_text", self.sibling_text.copy())
        all_info.setdefault("process_sibling_text", self.process_sibling_text)
        all_info.setdefault("child_text", self.child_text.copy())
        all_info.setdefault("process_child_text", self.process_child_text)
        all_info.setdefault("parent_text", self.parent_text)
        all_info.setdefault("dst_state", self.dst_state)
        all_info.setdefault("dst_state_not_sure", self.dst_state_not_sure)
        all_info.setdefault("format", "droidbot")
        return all_info


    def get_view_hash(self):
        view_tokens = []
        view_tokens.extend(["[type]", self.view_type])
        view_tokens.extend(["[text]", self.text])
        view_tokens.extend(["[content_desc]", self.content_desc])
        view_tokens.extend(["[hint]", self.hint])
        view_tokens.extend(["[resource_id]", self.resource_id])
        # view_tokens.extend(["[neighbor_text]", self.neighbor_text])
        # view_tokens.extend(["[sibling_text]", self.process_sibling_text])
        view_tokens.extend(["[child_text]", self.process_child_text])
        view_tokens.extend(["[parent_text]", self.parent_text])
        view_str = " ".join(view_tokens)
        view_str = re.sub(r"\s+", " ", view_str).strip()
        return hash(view_str)