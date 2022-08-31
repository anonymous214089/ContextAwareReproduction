import json
import re
import os
from PIL import Image, ImageStat
from lxml import etree
from lxml.etree import Element, SubElement, ElementTree

import shutil

view_idx = 0


def parse_layout_droidbot(json_path):
    json_path = json_path.replace("\\", "/")
    # print(json_path)
    clickable_views = {}
    find_view_str = []
    layout = json.load(open(json_path, "r", encoding="UTF-8"))
    img_path = json_path.replace("state_", "screen_").replace(".json", ".png")
    screen_img = Image.open(img_path)
    screen_id = layout["state_str"]
    if "com.android.launcher" in layout["foreground_activity"] and "launcher2" not in layout["foreground_activity"]:
        return clickable_views
    all_views = layout["views"]
    if all_views[0]["package"] == "com.android.browser":
        return clickable_views
    id2view = {}
    id2class = {}
    child_info = {}
    child_layout_count = {}
    clickable_bounds = []
    # resource_id_stat = {}
    for tview in all_views:
        id2view.setdefault(tview["temp_id"], tview)
        child_info.setdefault(tview["temp_id"], tview["children"])
        cur_clickable = tview["clickable"] or tview["long_clickable"] or tview["editable"]
        if cur_clickable:
            clickable_bounds.append(tview["bounds"])
            # if "resource_id" in tview.keys() and "/" in tview["resource_id"]:
            #     id_tokens = tokenize_resource_id(tview["resource_id"]).split(" ")
            #     for id_token in id_tokens:
            #         if id_token not in resource_id_stat.keys():
            #             resource_id_stat.setdefault(id_token, 1)
            #         else:
            #             resource_id_stat[id_token] += 1
    view_texts = {}
    text_pos = []
    for view_idx in range(max(id2view.keys()), -1, -1):
        if view_idx not in id2view.keys():
            continue
        view = id2view[view_idx]
        id2class.setdefault(view_idx, view["class"].replace("$", "."))
        cur_clickable = view["clickable"] or view["long_clickable"]
        cur_view_text = extract_view_text(view)
        view_texts.setdefault(view_idx, cur_view_text)
        if get_view_text(cur_view_text) != "none" and not cur_clickable:
            view_x = (view["bounds"][0][0] + view["bounds"][1][0]) / 2
            view_y = (view["bounds"][0][1] + view["bounds"][1][1]) / 2
            # text_pos.append([(view_center_x, view_center_y), get_view_text(cur_view_text)])
            in_clickable_view = False
            for cbound in clickable_bounds:
                if view_x > cbound[0][0] and view_x < cbound[1][0] and view_y > cbound[0][1] and view_y < cbound[1][1]:
                    in_clickable_view = True
                    break
            if not in_clickable_view and view_y > 0.08 * 1920:
                text_pos.append([(view_x, view_y), get_view_text(cur_view_text)])
                # if view_y > 0.08 * 1920 or get_view_text(cur_view_text).split(" ")[0].lower() == "add":
                #     text_pos.append([(view_x, view_y), get_view_text(cur_view_text)])
        child_text = []
        cur_child_layout_count = 0
        if view["class"][-6:].lower() == "layout":
            cur_child_layout_count += 1
        if view_idx in child_info.keys():
            for child_idx in child_info[view_idx]:
                if view_texts[child_idx]["text"] != "none":
                    child_posx = (id2view[child_idx]["bounds"][0][0] + id2view[child_idx]["bounds"][1][0]) / 2
                    child_posy = (id2view[child_idx]["bounds"][0][1] + id2view[child_idx]["bounds"][1][1]) / 2
                    child_text.append([view_texts[child_idx]["text"], child_posx, child_posy])
                else:
                    child_text.extend(id2view[child_idx]["child_text"])
                child_clickable = id2view[child_idx]["clickable"] or id2view[child_idx]["long_clickable"]
                if child_clickable:
                    cur_child_layout_count += child_layout_count[child_idx] + 1
                else:
                    cur_child_layout_count += child_layout_count[child_idx]
            child_text.sort(key=lambda x: (x[2], x[1]))
        # print(child_text)
        child_layout_count.setdefault(view_idx, cur_child_layout_count)
        view.setdefault("child_text", child_text)

    root_ele = Element("hierarchy", attrib={'id': '-1'})
    gen_xml_recursive(id2class, child_info, root_ele, 0, id2view)
    tree = ElementTree(root_ele)
    tree_text = etree.tostring(tree, encoding='utf8', method='xml', pretty_print=True)
    tree_text = str(tree_text, encoding="utf-8")
    id2xpath = get_id2xpath(tree_text)

    for view_idx, view in id2view.items():
        if view["bounds"][1][0] - view["bounds"][0][0] < 10 or view["bounds"][1][1] - view["bounds"][0][1] < 10:
            continue
        if view["bounds"][0][0] < 0 or view["bounds"][1][0] > 1080 or view["bounds"][0][1] < 0 or view["bounds"][1][1] > 1920:
            continue
        if view_idx not in id2xpath.keys():
            continue
        cur_clickable = view["clickable"]
        cur_clickable2 = view["content_description"] != None and "2022" in view["content_description"]
        cur_visible = view["visible"]
        cur_long_clickable = view["long_clickable"]
        cur_parent_idx = view["parent"]
        if not (cur_clickable or cur_clickable2) or cur_parent_idx == -1 or not cur_visible:
            continue
        cur_bounds = view["bounds"]
        # if cur_bounds[2] < cur_bounds[0] or cur_bounds[3] < cur_bounds[1]:
        #     continue
        cur_area = (cur_bounds[0][0] - cur_bounds[1][0]) * (cur_bounds[0][1] - cur_bounds[1][1])
        if cur_area < 0.001 * 1080 * 1920:
            continue
        view_img = screen_img.crop((cur_bounds[0][0], cur_bounds[0][1], cur_bounds[1][0], cur_bounds[1][1]))
        stat = ImageStat.Stat(view_img)
        img_mean = sum(stat.mean) / 3
        img_stddev = sum(stat.stddev) / 3
        # if img_stddev < 10 and (img_mean < 10 or img_mean > 246):
        # if (img_stddev < 10 and img_mean < 10) or (img_stddev < 5):
        #     # view_img.show()
        #     continue
        if child_layout_count[view_idx] > 7:
            # print("child_layout_count:", child_layout_count[view_idx], view["view_str"])
            continue
        cur_view_info = {}
        cur_view_info.setdefault("class", view["class"])
        cur_view_info.setdefault("clickable", cur_clickable)
        cur_view_info.setdefault("long_clickable", cur_long_clickable)
        cur_view_info.setdefault("type", get_view_type(view["class"]))
        cur_view_info.setdefault("bounds", view["bounds"])
        if "resource_id" not in view.keys() or view["resource_id"] == None:
            cur_view_info.setdefault("resource_id", "none")
        else:
            cur_view_info.setdefault("resource_id", tokenize_resource_id(view["resource_id"]))
        # set self text
        for text_type, text in view_texts[view_idx].items():
            cur_view_info.setdefault(text_type, text.lower())
        # set parent text
        uptime = 0
        use_parent_idx = cur_parent_idx
        cur_view_info.setdefault("parent_text", "none")
        while uptime < 3 and use_parent_idx in id2view.keys() and use_parent_idx in view_texts.keys():
            if get_view_text(view_texts[use_parent_idx]) != "none":
                cur_parent_text = get_view_text(view_texts[use_parent_idx]).lower()
                clean_parent_text = clean_non_ascii(cur_parent_text, 5)
                cur_view_info.setdefault("parent_text", clean_parent_text)
                break
            elif len(id2view[use_parent_idx]["child_text"]) > 0 and id2view[use_parent_idx]["child_text"][0][
                0] != "none":
                cur_parent_text = id2view[use_parent_idx]["child_text"][0][0].lower()
                clean_parent_text = clean_non_ascii(cur_parent_text, 5)
                cur_view_info.setdefault("parent_text", clean_parent_text)
                break
            use_parent_idx = id2view[use_parent_idx]["parent"]
            if use_parent_idx in child_info.keys() and len(child_info[use_parent_idx]) > 1:
                uptime += 1
        if uptime >= 3 or use_parent_idx not in id2view.keys():
            cur_view_info.setdefault("parent_text", "none")
        # set sibling text
        cur_sibling_text = []
        for sibling_idx in child_info[cur_parent_idx]:
            if sibling_idx == view_idx:
                continue
            sibling_view = id2view[sibling_idx]
            if sibling_view["clickable"] or sibling_view["long_clickable"]:
                continue
            cur_sibling_text.append(get_view_text(view_texts[sibling_idx]))
        cur_view_info.setdefault("sibling_text", cur_sibling_text)
        process_sibling_text = [clean_non_ascii(t) for t in cur_sibling_text if t != "none" and len(t.split()) <= 5]
        process_sibling_text = [t for t in process_sibling_text if t != "none"]
        if len(process_sibling_text) != 0:
            process_sibling_text = " , ".join(process_sibling_text)
            if len(process_sibling_text.split(" ")) > 15:
                sibling_text_token = process_sibling_text.split(" ")[:15]
                process_sibling_text = " ".join(sibling_text_token)
        else:
            process_sibling_text = "none"
        cur_view_info.setdefault("process_sibling_text", process_sibling_text)
        # set neighbor text
        neighbor_text = get_neighbor_text(view["bounds"], text_pos)
        clean_neighbor_text = clean_non_ascii(neighbor_text, 5)
        cur_view_info.setdefault("neighbor_text", clean_neighbor_text)
        # set child text
        cur_view_info.setdefault("child_text", view["child_text"])
        process_child_text = [clean_non_ascii(t[0]) for t in view["child_text"] if
                              t[0] != "none" and len(t[0].split()) <= 5]
        process_child_text = [t for t in process_child_text if t != "none"]
        if len(process_child_text) != 0:
            process_child_text = " , ".join(process_child_text)
            if len(process_child_text.split(" ")) > 15:
                child_text_token = process_child_text.split(" ")[:15]
                process_child_text = " ".join(child_text_token)
        else:
            process_child_text = "none"
        cur_view_info.setdefault("process_child_text", process_child_text)
        # add abs location
        cur_view_info.setdefault("abs_location", get_obj_abs_location(view["bounds"]))
        # add view_id
        cur_view_info.setdefault("view_id", view["view_str"] + "#" + str(view["bounds"]))
        cur_view_info.setdefault("screen_id", screen_id)
        cur_view_info.setdefault("xpath", id2xpath[view_idx])
        child_view_strs = []
        get_child_view_strs_recursive(view_idx, id2view, child_info, child_view_strs)
        cur_view_info.setdefault("child_view_strs", child_view_strs)

        # add to clickable_views
        refer_name = get_view_refer_name(cur_view_info)
        refer_name_clean1 = re.sub("[^a-z0-9]", " ", refer_name.lower())
        refer_name_clean1 = re.sub("\s+", " ", refer_name_clean1).strip()
        refer_name_clean2 = re.sub("[^a-z]", "", refer_name)

        # if len(refer_name_clean2) <= 1 or len(refer_name_clean1.split()) > 8 or refer_name == "none" or len(
        #         refer_name_clean2) / len(refer_name) < 0.5:
        #     continue
        view_symbol = view["view_str"] + "###" + str(find_view_str.count(view["view_str"]))
        # clickable_views.setdefault(view["view_str"], cur_view_info)
        find_view_str.append(view["view_str"])
        clickable_views.setdefault(view_symbol, cur_view_info)
    # print(clickable_views)
    return clickable_views


def get_neighbor_text(view_bounds, text_pos, screen_height=1920):
    if len(text_pos) == 0:
        return "none"
    view_center_x = (view_bounds[0][0] + view_bounds[1][0]) / 2
    view_center_y = (view_bounds[0][1] + view_bounds[1][1]) / 2
    text_dis = []
    for t in text_pos:
        x_dis = view_center_x - t[0][0]
        y_dis = view_center_y - t[0][1]
        if abs(y_dis) < 10:
            text_dis.append([0.5 * x_dis * x_dis, t[1]])
        elif y_dis > 50:
            text_dis.append([1.1 * x_dis * x_dis + 1.1 * y_dis * y_dis, t[1]])
        else:
            text_dis.append([x_dis * x_dis + y_dis * y_dis, t[1]])
        text_dis.append([x_dis * x_dis + 10 * y_dis * y_dis, t[1]])
    sort_text_dis = sorted(text_dis, key=(lambda x: x[0]))
    for sort_text in sort_text_dis:
        if sort_text[0] > 1 and sort_text[0] < screen_height * screen_height / 36:
            return sort_text[1]
    # return sort_text_dis[0][1]
    return "none"


def tokenize_resource_id(resource_id: str):
    resource_id = resource_id.split("/")[-1]
    resource_id = re.sub(r'([a-z])([A-Z])', r'\1 \2', resource_id).lower()
    resource_id = re.sub(r"[^a-z0-9]", " ", resource_id)
    resource_id = re.sub(r"\s+", " ", resource_id).strip()
    return resource_id


def extract_view_text(view):
    cur_text = {}
    if "text" not in view.keys() or view["text"] == None or view["class"][-8:].lower() == "edittext":
        cur_text.setdefault("text", "none")
    else:
        if type(view["text"]) == type([]):
            cur_text.setdefault("text", clean_non_ascii(view["text"][0], 100))
        else:
            cur_text.setdefault("text", clean_non_ascii(view["text"], 100))
    # if "content_description" not in view.keys() or view["content_description"] == None or view["class"][
    #                                                                                -8:].lower() == "edittext":
    if "content_description" not in view.keys() or view["content_description"] == None:
        cur_text.setdefault("content_desc", "none")
    else:
        if type(view["content_description"]) == type([]):
            cur_text.setdefault("content_desc", clean_non_ascii(view["content_description"][0], 100))
        else:
            cur_text.setdefault("content_desc", clean_non_ascii(view["content_description"], 100))
    if "hint" not in view.keys() or view["hint"] == None:
        cur_text.setdefault("hint", "none")
    else:
        if type(view["hint"]) == type([]):
            cur_text.setdefault("hint", clean_non_ascii(view["hint"][0], 100))
        else:
            cur_text.setdefault("hint", clean_non_ascii(view["hint"], 100))
    return cur_text


def get_view_text(view_text):
    if view_text["text"] != "none":
        return view_text["text"]
    if view_text["content_desc"] != "none":
        return view_text["content_desc"]
    if view_text["hint"] != "none":
        return view_text["hint"]
    return "none"


def get_obj_abs_location(obj_bounds):
    abs_location = [["top left corner", "top", "top right corner"], ["left", "center", "right"],
                    ["bottom left corner", "bottom", "bottom right corner"]]
    obj_posx = (obj_bounds[0][0] + obj_bounds[1][0]) / 2
    obj_posy = (obj_bounds[0][1] + obj_bounds[1][1]) / 2
    width_idx = int((3 * obj_posx) // 1080)
    height_idx = int((3 * obj_posy) // 1920)
    return abs_location[height_idx][width_idx]


def get_view_type(view_class: str):
    default_type = ["button", "imagebutton", "imageview", "textview", "checkbox", "edittext", "radiobutton", "switch"]
    if view_class.split(".")[-1].lower() in default_type:
        return view_class.split(".")[-1].lower()
    else:
        view_class = view_class.split(".")[-1]
        view_class = re.sub(r'([a-z])([A-Z])', r'\1 \2', view_class).lower()
        view_class = re.sub(r"[^a-z0-9]", " ", view_class)
        view_class = re.sub(r"\s+", " ", view_class).strip()
        return view_class


def gen_view_str(view):
    view_tokens = []
    view_tokens.extend(["[type]", view["type"]])
    view_tokens.extend(["[text]", view["text"]])
    view_tokens.extend(["[content_desc]", view["content_desc"]])
    view_tokens.extend(["[hint]", view["hint"]])
    view_tokens.extend(["[resource_id]", view["resource_id"]])
    view_tokens.extend(["[abs_location]", view["abs_location"]])
    view_tokens.extend(["[neighbor_text]", view["neighbor_text"]])
    view_tokens.extend(["[sibling_text]", view["process_sibling_text"]])
    view_tokens.extend(["[child_text]", view["process_child_text"]])
    view_tokens.extend(["[parent_text]", view["parent_text"]])
    view_str = " ".join(view_tokens)
    view_str = re.sub(r"\s+", " ", view_str).strip()
    return view_str


def gen_xml_recursive(id2class, child_dict, parent, cur_id, id2view):
    # print("in:", cur_id)
    view = id2view[cur_id]
    if view["bounds"][1][0] - view["bounds"][0][0] <= 0 or view["bounds"][1][1] - view["bounds"][0][1] <= 0:
        # print("pass1:", cur_id)
        return
    if view["bounds"][0][0] < 0 or view["bounds"][1][0] > 1080 or view["bounds"][0][1] < 0 or view["bounds"][1][
        1] > 1920:
        # print("pass2:", cur_id)
        return
    cur_class = id2class[cur_id]
    # print("out:", cur_id)
    cur_ele = SubElement(parent, cur_class, attrib={'id': str(cur_id)})
    for child_id in child_dict[cur_id]:
        gen_xml_recursive(id2class, child_dict, cur_ele, child_id, id2view)


def get_child_view_strs_recursive(view_id, id2view: dict, child_info: dict, child_view_strs: list):
    child_ids = child_info[view_id]
    for child_id in child_ids:
        child_view = id2view[child_id]
        if child_view["clickable"] or child_view["long_clickable"]:
            continue
        child_view_str = child_view["view_str"]
        child_view_strs.append(child_view_str)
        get_child_view_strs_recursive(child_id, id2view, child_info, child_view_strs)



def get_id2xpath(xml_page):
    xml_page = xml_page.replace('<?xml version="1.0" encoding="UTF-8"?>', "")
    xml_parser = etree.XML(xml_page)
    tree = xml_parser.getroottree()
    all_nodes = xml_parser.xpath('//*')
    id2xpath = {}
    xpath = []
    for node in all_nodes:
        xpath.append(tree.getpath(node))
    for node, path in zip(all_nodes, xpath):
        node_id = int(node.attrib["id"])
        id2xpath.setdefault(node_id, path)
    return id2xpath


def clean_non_ascii(ori_str, max_len=5):
    clean_str = re.sub("[^\x00-\x7f]", " ", ori_str.lower())
    # clean_str = re.sub("[.,]", " ", clean_str.lower())
    clean_str = re.sub("\s+", " ", clean_str).strip()
    if len(clean_str.split()) > max_len:
        clean_str_tokens = clean_str.split()[:max_len]
        clean_str = " ".join(clean_str_tokens)
    if len(clean_str.strip()) == 0:
        return "none"
    return clean_str


def get_view_refer_name(view_info):
    # Priority 0: for EditText, return its resource id for name
    if view_info["class"][-8:].lower() == "edittext" and view_info["resource_id"] != "none" and len(
            view_info["resource_id"].split()) > 1:
        # print("Priority 0: for EditText, return its resource id for name")
        return view_info["resource_id"].lower()
    # Priority 1: text from self
    if view_info["text"] != "none":
        # print("Priority 1: text from self, text")
        return view_info["text"].lower()
    if view_info["content_desc"] != "none":
        # print("Priority 1: text from self, content_desc")
        return view_info["content_desc"].lower()
    if view_info["hint"] != "none":
        # print("Priority 1: text from self, hint")
        return view_info["hint"].lower()
    # Priority 2: case layout, text from child
    if view_info["class"][-6:].lower() == "layout" and len(view_info["child_text"]) > 0:
        # print("Priority 2: case layout, text from child")
        return view_info["child_text"][0][0].lower()
    # Priority 3: return not none sibling text
    if len(view_info["sibling_text"]) > 0:
        for sibling_text in view_info["sibling_text"]:
            if sibling_text != "none":
                # print("Priority 3: return not none sibling text")
                return sibling_text.lower()
    # Priority 4: return only one child_text
    if len(view_info["child_text"]) == 1 and view_info["child_text"][0] != "none":
        # print("Priority 4: return only one child_text")
        return view_info["child_text"][0][0].lower()

    # Priority 5: view's resource id longer than 3 words, it may be a meaningful identifier
    if view_info["resource_id"] != "none" and len(view_info["resource_id"].split()) > 2:
        # print("Priority 5: view's resource id longer than 3 words, it may be a meaningful identifier
        return view_info["resource_id"].lower()

    # Priority 6: return neighbor text
    # print("Priority 6: return neighbor text")
    return view_info["neighbor_text"].lower()


def save_view_image(view_idx, img_path, bounds, save_dir):
    img = Image.open(img_path)
    im = img.crop((bounds[0][0], bounds[0][1], bounds[1][0], bounds[1][1]))
    cut_name = save_dir + "/" + str(view_idx) + ".jpg"
    im.save(cut_name)


if __name__ == '__main__':
    # all_data = {}
    # for i in tqdm(range(2000)):
    #     extract_clickable_view(i)
    #     # show_extract_clickable_view(i)
    # save_file = open("rico_click_match.pkl","wb")
    # pickle.dump(all_data, save_file)
    res = parse_layout_droidbot(r"../Data/MyData/DroidBotRes/16_7LPdWcaW-GrowTracker-Android-87/states/state_2022-06-13_172149.json")
    # print(parse_layout_droidbot(r"..\Data\RecDroid2\DroidBotRes\30.Anki-Android\states\state_2022-06-17_182347.json"))
    # for k, v in res.items():
    #     print(v["content_desc"])
    for k, v in res.items():
        print(v)