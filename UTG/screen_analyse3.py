import json
import os

import Levenshtein
import cv2
import xml.etree.ElementTree as ET
from lxml import etree
from lxml.etree import Element, SubElement, ElementTree
import re
import shutil


def extract_views_on_screen(state_json_path):
    # state_json_path = "../Data/RecDroid/DroidBotRes/13.librenews_refresh_s/states/state_2021-12-14_132240.json"
    # exclude_parents = ["RecyclerView"]
    state_json_path = state_json_path.replace("\\", "/")
    if not os.path.exists(state_json_path):
        return {"activity": ".Launcher", "views_on_screen": set(), "clickable_views_on_screen": set(), "all_text": []}
    state_json = json.load(open(state_json_path, "r"))
    activity = state_json["foreground_activity"]
    views_on_screen = set()
    clickable_views_on_screen = set()
    all_text = []
    id2class = {}
    id2view = {}
    child_info = {}
    parent_info = {}
    for view in state_json["views"]:
        id2class.setdefault(view["temp_id"], view["class"].replace("$", "."))
        id2view.setdefault(view["temp_id"], view)
        child_info.setdefault(view["temp_id"], view["children"])
        parent_info.setdefault(view["temp_id"], view["parent"])
    root_ele = Element("hierarchy", attrib={'id': '-1'})
    gen_xml_recursive(id2class, child_info, root_ele, 0, id2view)
    tree = ElementTree(root_ele)
    tree_text = etree.tostring(tree, encoding='utf8', method='xml', pretty_print=True)
    tree_text = str(tree_text, encoding="utf-8")
    # with open("../Temp/test2.xml", "w", encoding='utf8') as f:
    #     f.write(tree_text)
    id2xpath = get_id2xpath(tree_text)
    for view_idx, xpath in id2xpath.items():
        # exclude_text = False
        # cur_parent = parent_info[view_idx]
        # while cur_parent > 0:
        #     parent_class = id2view[cur_parent]["class"].split(".")[-1]
        #     if parent_class in exclude_parents:
        #         exclude_text = True
        #         break
        #     cur_parent = parent_info[cur_parent]

        if view_idx not in id2view.keys():
            continue
        view = id2view[view_idx]
        if "com.android.launcher" in view["package"] or "com.android.browser" in view["package"]:
            continue
        clickable = (view["clickable"] or view["long_clickable"]) and view["enabled"] and view["visible"]
        exclude_ids = ["com.ichi2.anki:id/deckpicker_deck", "net.gsantner.markor:id/opoc_filesystem_item__root"]
        not_list = view["class"].split(".")[-1] != "ListView" and view["class"].split(".")[-1] != "RecyclerView"
        clickable = clickable and (view["resource_id"] not in exclude_ids) and not_list
        bounds_arr = view["bounds"]
        view_width = view["bounds"][1][0] - view["bounds"][0][0]
        view_height = view["bounds"][1][1] - view["bounds"][0][1]
        if view_width < 10 or view_height < 10:
            continue
        if view["bounds"][0][0] < 0 or view["bounds"][1][0] > 1080 or view["bounds"][0][1] < 0 or view["bounds"][1][
            1] > 1920:
            continue
        if not view["visible"]:
            continue
        bounds_str = str(view_width // 10) + "," + str(view_height // 10)
        if bounds_str == "108,192":
            bounds_str = "108,179"
        # bounds_str = str(view_width) + "," + str(view_height)
        views_on_screen.add(xpath + "#" + bounds_str)

        if check_text_exclude(view["text"], xpath):
            all_text.append(view["text"])
        if clickable:
            exclude_flag1 = "RecyclerView" in xpath
            # exclude_flag2 = "ListView" in xpath and view_width < 540
            exclude_flag2 = "ListView" in xpath and view["package"] != "com.ichi2.anki"
            exclude_flag = exclude_flag1 or exclude_flag2
            cur_symbol = xpath + "#" + bounds_str
            if exclude_flag:
                if not check_contain(cur_symbol, clickable_views_on_screen):
                    clickable_views_on_screen.add(cur_symbol)
            else:
                clickable_views_on_screen.add(cur_symbol)
    # print(views_on_screen)
    # if len(all_text) == 0:
    #     text_hash = 0
    # else:
    #     all_text_str = "#".join(all_text)
    #     text_hash = hash(all_text_str)
    return {"activity": activity, "views_on_screen": views_on_screen, "all_text": all_text,
            "clickable_views_on_screen": clickable_views_on_screen}


# def gen_xml_recursive(id2class, child_dict, parent, cur_id):
#     cur_class = id2class[cur_id]
#     cur_ele = SubElement(parent, cur_class, attrib={'id': str(cur_id)})
#     for child_id in child_dict[cur_id]:
#         gen_xml_recursive(id2class, child_dict, cur_ele, child_id)


def gen_xml_recursive(id2class, child_dict, parent, cur_id, id2view):
    view = id2view[cur_id]
    if view["bounds"][1][0] - view["bounds"][0][0] <= 0 or view["bounds"][1][1] - view["bounds"][0][1] <= 0:
        # print("pass1:", cur_id)
        return
    if view["bounds"][0][0] < 0 or view["bounds"][1][0] > 1080 or view["bounds"][0][1] < 0 or view["bounds"][1][
        1] > 1920:
        # print("pass2:", cur_id)
        return
    if not view["visible"]:
        return
    cur_class = id2class[cur_id]
    # print("out:", cur_id)
    cur_ele = SubElement(parent, cur_class, attrib={'id': str(cur_id)})
    for child_id in child_dict[cur_id]:
        gen_xml_recursive(id2class, child_dict, cur_ele, child_id, id2view)


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


def check_state_is_same_old(state_info1, state_info2, threshold=0.9):
    if state_info1["activity"].split(".")[-1] != state_info2["activity"].split(".")[-1]:
        return False
    union_views = state_info1["views_on_screen"].union(state_info2["views_on_screen"])
    inter_views = state_info1["views_on_screen"].intersection(state_info2["views_on_screen"])
    if len(union_views) == 0:
        jaccard = 0
    else:
        jaccard = len(inter_views) / len(union_views)
    # print(jaccard)
    # print(state_info1["views_on_screen"] - inter_views)
    # print(state_info2["views_on_screen"] - inter_views)
    if jaccard < threshold:
        return False
    else:
        return True


def check_state_is_same(state_info1, state_info2, threshold=0.7, print_diff=False):
    if state_info1["activity"].split(".")[-1] != state_info2["activity"].split(".")[-1]:
        return False
    view_count_1 = max(len(state_info1["views_on_screen"]), len(state_info2["views_on_screen"]))
    view_count_2 = min(len(state_info1["views_on_screen"]), len(state_info2["views_on_screen"]))
    if view_count_2 == 0 or view_count_2 / view_count_1 < threshold:
        # print(view_count_1, view_count_2)
        return False
    view_count_1 = max(len(state_info1["clickable_views_on_screen"]), len(state_info1["clickable_views_on_screen"]))
    view_count_2 = min(len(state_info1["clickable_views_on_screen"]), len(state_info2["clickable_views_on_screen"]))
    clickable_union_views = len(
        state_info1["clickable_views_on_screen"].union(state_info2["clickable_views_on_screen"]))
    clickable_inter_views = len(
        state_info1["clickable_views_on_screen"].intersection(state_info2["clickable_views_on_screen"]))
    if view_count_2 == 0 or clickable_inter_views / clickable_union_views < 0.85:
        # print(view_count_1, view_count_2)
        return False
    views_on_screen1 = set()
    for xpath in state_info1["views_on_screen"]:
        views_on_screen1.add(re.sub(r"\[\d+]", "", xpath))
    views_on_screen2 = set()
    for xpath in state_info2["views_on_screen"]:
        views_on_screen2.add(re.sub(r"\[\d+]", "", xpath))
    union_views = views_on_screen1.union(views_on_screen2)
    inter_views = views_on_screen1.intersection(views_on_screen2)
    if len(union_views) == 0:
        jaccard = 0
    else:
        jaccard = len(inter_views) / len(union_views)
    if print_diff:
        print(jaccard)
        print(len(state_info1["views_on_screen"]))
        print(len(state_info2["views_on_screen"]))
        diff1 = views_on_screen1 - inter_views
        diff2 = views_on_screen2 - inter_views
        for item1 in diff1:
            max_sim = 999
            max_sim_item = ""
            for item2 in diff2:
                dis = Levenshtein.distance(item1, item2)
                if dis < max_sim:
                    max_sim = dis
                    max_sim_item = item2
            print("max_sim", max_sim)
            print("item 1", item1)
            print("item 2", max_sim_item)
            print("")
        print(len(diff1))
        print(len(diff2))
    if jaccard < threshold:
        return False
    else:
        return True


def get_state_sim_old(state_info1, state_info2, prinf_diff=False):
    if state_info1["activity"].split(".")[-1] != state_info2["activity"].split(".")[-1]:
        return -1
    union_views = state_info1["views_on_screen"].union(state_info2["views_on_screen"])
    inter_views = state_info1["views_on_screen"].intersection(state_info2["views_on_screen"])
    jaccard = len(inter_views) / len(union_views)
    if prinf_diff:
        print(state_info1["views_on_screen"] - inter_views)
        print(state_info2["views_on_screen"] - inter_views)
    return jaccard


def get_state_sim(state_info1, state_info2, prinf_diff=False):
    if state_info1["activity"].split(".")[-1] != state_info2["activity"].split(".")[-1]:
        if "launcher2" not in state_info1["activity"] and "launcher2" not in state_info2[
            "activity"] and "unknown" not in state_info1["activity"] and "unknown" not in state_info2["activity"]:
            return -1.1
    text_set1 = set(state_info1["all_text"])
    text_set2 = set(state_info2["all_text"])
    clickable_views1 = state_info1["clickable_views_on_screen"]
    clickable_views2 = state_info2["clickable_views_on_screen"]
    clickable_view_count1 = max(len(clickable_views1), len(clickable_views2))
    clickable_view_count2 = min(len(clickable_views1), len(clickable_views2))
    text_inter_set = text_set1.intersection(text_set2)
    text_union_set = text_set1.union(text_set2)

    # click_union_size = len(clickable_views1.union(clickable_views2))
    # click_inter_size = len(clickable_views1.intersection(clickable_views2))
    simple_cv1 = set()
    for tcv in clickable_views1:
        short_tcv = re.sub(r"\[\d+]", "", tcv.split("#")[0])
        simple_cv1.add(short_tcv)
    simple_cv2 = set()
    for tcv in clickable_views2:
        short_tcv = re.sub(r"\[\d+]", "", tcv.split("#")[0])
        simple_cv2.add(short_tcv)
    click_union_size = len(simple_cv1.union(simple_cv2))
    click_inter_size = len(simple_cv1.intersection(simple_cv2))

    # if len(text_set1) > 0 and len(text_set2) > 0 and len(text_union_set - text_inter_set) == 0 \
    #         and clickable_view_count2 / clickable_view_count1 >= 0.7:
    #     return 1
    if clickable_view_count1 > 0 and clickable_view_count2 / clickable_view_count1 < 0.86:
        if prinf_diff:
            print(clickable_view_count1)
            print(clickable_view_count1)
        return -1.2

    if click_union_size > 0 and click_inter_size / click_union_size < 0.8:
        if prinf_diff:
            # print(len(clickable_views1))
            # print(len(clickable_views2))
            print(click_inter_size, click_union_size)
            print(clickable_views1)
            print(clickable_views2)
        return -1.3
    if len(text_set1) >= 1 and len(text_set2) >= 1 and clickable_view_count2 < 5:
        has_listview = False
        pattern = re.compile("\[\d+]")
        max_listview_items = -1
        for view_key in state_info1["views_on_screen"]:
            if "ListView" in view_key:
                list_item_idxs = pattern.findall(view_key)
                for item_idx in list_item_idxs:
                    item_idx_num = int(item_idx[1:-1])
                    if item_idx_num > max_listview_items:
                        max_listview_items = item_idx_num
        if max_listview_items > 4:
            has_listview = True
        except_text = ["cancel", "ok", "done", 'import cards', "playlist", "puzzle", "learn more"]
        # text_inter_set2 = []
        # for text in text_inter_set:
        #     if text.lower() not in except_text:
        #         text_inter_set2.append(text)
        # if len(text_inter_set2) == 0:
        #     if prinf_diff:
        #         print(text_set1)
        #         print(text_set2)
        #     return -1.4
        clean_text1 = set()
        for text in text_set1:
            if text.lower() not in except_text:
                clean_t = re.sub(r"[^a-zA-Z ]", " ", text)
                clean_t = re.sub(r"\s+", " ", clean_t).strip()
                if len(clean_t) > 0:
                    clean_text1.add(clean_t)
        clean_text2 = set()
        for text in text_set2:
            if text.lower() not in except_text:
                clean_t = re.sub(r"[^a-zA-Z ]", " ", text)
                clean_t = re.sub(r"\s+", " ", clean_t).strip()
                if len(clean_t) > 0:
                    clean_text2.add(clean_t)
        clean_inter = clean_text1.intersection(clean_text2)
        if len(clean_inter) == 0 and len(clean_text1) > 0 and len(clean_text2) > 0 and not has_listview:
            if prinf_diff:
                print(text_set1, clean_text1)
                print(clickable_view_count2)
                print(text_set2, clean_text2)
            return -1.4
    views_on_screen_ori1 = set()
    for xpath in state_info1["views_on_screen"]:
        ori_xpath = re.sub(r"#\d+,\d+", "", xpath)
        # if ori_xpath[-1] == "]":
        #     short_xpath = re.sub(r"\[\d+]", "", ori_xpath[:-3]) + ori_xpath[-3:]
        #     views_on_screen_ori1.add(short_xpath)
        # else:
        #     views_on_screen_ori1.add(re.sub(r"\[\d+]", "", ori_xpath))
        views_on_screen_ori1.add(ori_xpath)
    views_on_screen_ori2 = set()
    for xpath in state_info2["views_on_screen"]:
        ori_xpath = re.sub(r"#\d+,\d+", "", xpath)
        # if ori_xpath[-1] == "]":
        #     short_xpath = re.sub(r"\[\d+]", "", ori_xpath[:-3]) + ori_xpath[-3:]
        #     views_on_screen_ori2.add(short_xpath)
        # else:
        #     views_on_screen_ori2.add(re.sub(r"\[\d+]", "", ori_xpath))
        views_on_screen_ori2.add(ori_xpath)
    union_views_ori = views_on_screen_ori1.union(views_on_screen_ori2)
    inter_views_ori = views_on_screen_ori1.intersection(views_on_screen_ori2)
    if len(union_views_ori) > 0:
        jaccard1 = len(inter_views_ori) / len(union_views_ori)
    else:
        jaccard1 = 0
    views_on_screen1 = set()
    for xpath in state_info1["views_on_screen"]:
        # views_on_screen1.add(re.sub(r"\[\d+]", "", xpath))
        views_on_screen1.add(process_xpath(xpath))
    views_on_screen2 = set()
    for xpath in state_info2["views_on_screen"]:
        # views_on_screen2.add(re.sub(r"\[\d+]", "", xpath))
        views_on_screen2.add(process_xpath(xpath))
    union_views = views_on_screen1.union(views_on_screen2)
    inter_views = views_on_screen1.intersection(views_on_screen2)
    if len(union_views) == 0:
        return 0
    jaccard = len(inter_views) / len(union_views)
    if prinf_diff:
        print("inter_views_ori:", len(inter_views_ori), "union_views_ori:", len(union_views_ori))
        views_on_screen1 = list(views_on_screen1)
        views_on_screen1.sort(key=lambda x: len(x))
        views_on_screen2 = list(views_on_screen2)
        views_on_screen2.sort(key=lambda x: len(x))
        # print("inter_views_ori:", inter_views_ori)
        print("inter_views:", len(inter_views), "union_views:", len(union_views))
        for view1 in views_on_screen_ori1:
            if view1 in views_on_screen_ori2:
                print("find view1", view1)
                continue
            most_sim_view = "#Can't Find"
            min_dis = 999
            for view2 in views_on_screen_ori2:
                cur_dis = Levenshtein.distance(view1, view2)
                if cur_dis < min_dis:
                    min_dis = cur_dis
                    if cur_dis < 8:
                        most_sim_view = view2
            print("view 1:", view1)
            print("view 2:", most_sim_view)
        # print("views_on_screen1:", views_on_screen1)
        # print("views_on_screen2:", views_on_screen2)
        # print("views_on_screen1 - inter_views", views_on_screen1 - inter_views)
        # print("views_on_screen2 - inter_views", views_on_screen2 - inter_views)
    if jaccard > 0.75:
        return jaccard
    elif jaccard1 > 0.75:
        return jaccard1 - 0.1
    else:
        return jaccard


def process_xpath(xpath: str):
    bounds_arr = xpath.split("#")[-1]
    ori_xpath = re.sub(r"#\d+,\d+", "", xpath)
    if ori_xpath[-1] == "]":
        short_xpath = re.sub(r"\[\d+]", "", ori_xpath[:-3]) + ori_xpath[-3:]
    else:
        short_xpath = re.sub(r"\[\d+]", "", ori_xpath)
    new_xpath = short_xpath + "#" + bounds_arr
    return new_xpath


def merge_same_state(prj_dir, debug=False):
    id2path = {}
    id2image = {}
    scroll_state = {}
    utg_lines = open(os.path.join(prj_dir, "utg.js"), "r").readlines()
    utg_json = json.loads("".join(utg_lines[1:]))
    for node in utg_json["nodes"]:
        state_json_path = node["image"].replace("screen_", "state_").replace(".png", ".json").replace("\\", "/")
        state_json_path = os.path.join(prj_dir, state_json_path)
        id2path.setdefault(node["id"], state_json_path)
        id2image.setdefault(node["id"], os.path.join(prj_dir, node["image"].replace("\\", "/")))
    for edge in utg_json["edges"]:
        if len(edge["events"]) > 1:
            continue
        for event in edge["events"]:
            event_type = event["event_type"]
            event_str = event["event_str"]
            swipe_horizon = "direction=LEFT" in event_str or "direction=RIGHT" in event_str
            if event_type == "scroll" and edge["to"] != edge["from"] and not swipe_horizon:
                scroll_state.setdefault(edge["to"], edge["from"])
    id2detail = {}
    for node_id, state_path in id2path.items():
        node_detail = extract_views_on_screen(state_path)
        id2detail.setdefault(node_id, node_detail)
    # node_id1 = "38506ef9bbaed690261a489e9b8f61d4"
    # node_id2 = "dfc31dd44f2eb25f88258801fe91cafb"
    # check_state_is_same(id2detail[node_id1], id2detail[node_id2], threshold=0.9)
    # return
    state2id = {}
    state2detail = {}
    if len(utg_json["nodes"]) > 1:
        for node_id, node_detail in id2detail.items():
            # if len(node_detail["views_on_screen"]) == 0:
            #     continue
            find_exist_same = False
            if "com.android.launcher" in node_detail[
                "activity"] and "state_0" in state2detail.keys() and "launcher2" not in node_detail["activity"]:
                state2id["state_0"].append(node_id)
                state2detail["state_0"]["views_on_screen"] = state2detail["state_0"]["views_on_screen"].union(
                    node_detail["views_on_screen"])
                continue
            # if node_detail["activity"] == "org.schabi.newpipe/.MainActivity" and len(node_detail["all_text"]) > 0 and \
            #         node_detail["all_text"][0] == "Trending":
            #     if "state_1" not in state2id.keys():
            #         state_key = "state_1"
            #         state2id.setdefault(state_key, [node_id])
            #         new_state_detail = {"activity": node_detail["activity"], "all_text": node_detail["all_text"],
            #                             "clickable_views_on_screen": node_detail["clickable_views_on_screen"],
            #                             "views_on_screen": node_detail["views_on_screen"]}
            #         state2detail.setdefault(state_key, new_state_detail)
            #     else:
            #         state2detail["state_1"]["views_on_screen"] = state2detail["state_1"]["views_on_screen"].union(
            #             node_detail["views_on_screen"])
            #         state2id["state_1"].append(node_id)
            #     continue
            if len(node_detail["all_text"]) <= 2 and len(
                    node_detail["all_text"]) > 0 and "state_0" in state2detail.keys():
                match_crash = re.match(r"Unfortunately, .*? has stopped.", node_detail["all_text"][0])
                if match_crash:
                    state2id["state_0"].append(node_id)
                    continue
            for state_id, state_detail in state2detail.items():
                # is_same_state = check_state_is_same(node_detail, state_detail, threshold=0.68)
                state_sim = get_state_sim(node_detail, state_detail)
                is_same_state = state_sim > 0.78
                if is_same_state:
                    state2id[state_id].append(node_id)
                    before_len = len(state_detail["views_on_screen"])
                    # state_detail["views_on_screen"] = state_detail["views_on_screen"].union(node_detail["views_on_screen"])
                    # new_len = len(state_detail["views_on_screen"])
                    # if new_len > before_len:
                    #     print("expand:", state_id, id2path[node_id])
                    find_exist_same = True
                    break
            if not find_exist_same:
                if node_id in scroll_state.keys():
                    ori_id = scroll_state[node_id]
                    temp_id2state = {}
                    for state_id, tnode_ids in state2id.items():
                        for tnode_id in tnode_ids:
                            temp_id2state.setdefault(tnode_id, state_id)
                    if ori_id in temp_id2state.keys():
                        ori_state = temp_id2state[ori_id]
                        if "9999" not in ori_state:
                            state_key = ori_state + "9999"
                        else:
                            state_key = ori_state
                        if state_key not in state2id.keys():
                            state_key = ori_state + "9999"
                            state2id.setdefault(state_key, [node_id])
                            new_state_detail = {"activity": node_detail["activity"],
                                                "all_text": node_detail["all_text"],
                                                "clickable_views_on_screen": node_detail["clickable_views_on_screen"],
                                                "views_on_screen": node_detail["views_on_screen"]}
                            state2detail.setdefault(state_key, new_state_detail)
                        else:
                            state2id[state_key].append(node_id)
                    else:
                        pass
                else:
                    new_state_idx = len(state2detail.keys())
                    # if new_state_idx == 1 and len(node_detail["clickable_views_on_screen"]) == 0 and "MainActivity" not in \
                    #         node_detail["activity"]:
                    if new_state_idx == 1 and len(node_detail["clickable_views_on_screen"]) == 0:
                        if len(node_detail["all_text"]) == 0 and node_detail[
                            "activity"] != "com.hiddenramblings.tagmo/.MainActivity_":
                            continue
                        if len(node_detail["all_text"]) > 0 and 'Opening collection…' in node_detail["all_text"]:
                            continue
                        if len(node_detail["all_text"]) > 0 and 'ODK Collect' in node_detail["all_text"]:
                            continue
                    state_key = "state_" + str(new_state_idx)
                    state2id.setdefault(state_key, [node_id])
                    new_state_detail = {"activity": node_detail["activity"], "all_text": node_detail["all_text"],
                                        "clickable_views_on_screen": node_detail["clickable_views_on_screen"],
                                        "views_on_screen": node_detail["views_on_screen"]}
                    state2detail.setdefault(state_key, new_state_detail)
    else:
        print("### not merge state")
        for node_id, node_detail in id2detail.items():
            if "com.android.launcher" in node_detail["activity"] and "state_0" in state2detail.keys():
                state2id["state_0"].append(node_id)
                state2detail["state_0"]["views_on_screen"] = state2detail["state_0"]["views_on_screen"].union(
                    node_detail["views_on_screen"])
                continue
            if len(node_detail["all_text"]) == 2 and "state_0" in state2detail.keys():
                match_crash = re.match(r"Unfortunately, .*? has stopped.", node_detail["all_text"][0])
                if match_crash and node_detail["all_text"][1] == "OK":
                    state2id["state_0"].append(node_id)
                    continue
            new_state_idx = len(state2detail.keys())
            if new_state_idx == 1 and len(node_detail["clickable_views_on_screen"]) == 0 and "MainActivity" not in \
                    node_detail["activity"]:
                continue
            state_key = "state_" + str(new_state_idx)
            state2id.setdefault(state_key, [node_id])
            new_state_detail = {"activity": node_detail["activity"], "all_text": node_detail["all_text"],
                                "clickable_views_on_screen": node_detail["clickable_views_on_screen"],
                                "views_on_screen": node_detail["views_on_screen"]}
            state2detail.setdefault(state_key, new_state_detail)
    # print("###" * 20)
    # print(check_state_is_same(state2detail["state_1"], state2detail["state_6"]))
    if os.path.exists("../Temp/screens/"):
        shutil.rmtree("../Temp/screens/")
        os.mkdir("../Temp/screens/")
    for state_id, node_ids in state2id.items():
        if debug:
            print(state_id, ":", node_ids)
            print(len(state2detail[state_id]["clickable_views_on_screen"]), state2detail[state_id]["all_text"])
        for i, node_id in enumerate(node_ids):
            state_img_path = id2image[node_id]
            if os.path.exists(state_img_path):
                img = cv2.imread(state_img_path)
                img = cv2.resize(img, (540, 960), interpolation=cv2.INTER_CUBIC)
                if debug:
                    print("\t" + id2path[node_id])
                cv2.imwrite("../Temp/screens/" + state_id + "_" + str(i + 1) + ".png", img)
                # if not debug:
                #     break
    id2state = {}
    for state_id, node_ids in state2id.items():
        for node_id in node_ids:
            id2state.setdefault(node_id, state_id)
    return id2state, state2id, state2detail, id2path


def extract_views_on_xml_screen(page_source):
    page_source = page_source.replace("&#", "")
    views_on_screen = set()
    clickable_views_on_screen = set()
    # doc = page_source.replace('<?xml version="1.0" encoding="UTF-8"?>', "")
    # doc = re.sub(r"<\?xml version='1\.0'.*?encoding='UTF-8'.*?>", "", page_source)
    doc = re.sub(r"<\?xml version=['\"]1\.0['\"] encoding=['\"]UTF-8['\"].*?>", "", page_source)
    xml_parser = etree.XML(doc)
    tree = xml_parser.getroottree()
    all_nodes = xml_parser.xpath('//*')
    all_text = []
    for node in all_nodes:
        attribs = node.attrib
        if "clickable" not in attribs.keys():
            continue
        clickable = (attribs["clickable"] == "true") or (attribs["long-clickable"] == "true")
        clickable = clickable and (attribs["enabled"] == "true")
        cur_id = attribs["resource-id"] if "resource-id" in attribs.keys() else "none"
        exclude_ids = ["com.ichi2.anki:id/deckpicker_deck", "net.gsantner.markor:id/opoc_filesystem_item__root"]
        not_list = attribs["class"].split(".")[-1] != "ListView" and attribs["class"].split(".")[-1] != "RecyclerView"
        clickable = clickable and (cur_id not in exclude_ids) and not_list
        bounds_str = attribs["bounds"]
        bounds_str = "[" + bounds_str.replace("][", "],[") + "]"
        bounds_arr = eval(bounds_str)
        view_width = bounds_arr[1][0] - bounds_arr[0][0]
        view_height = bounds_arr[1][1] - bounds_arr[0][1]
        if "com.android.launcher" in attribs["package"] or "com.android.browser" in attribs["package"]:
            continue
        if view_width < 10 or view_height < 10:
            continue
        if bounds_arr[0][0] < 0 or bounds_arr[1][0] > 1080 or bounds_arr[0][1] < 0 or bounds_arr[1][1] > 1920:
            continue
        bounds_str = str(view_width // 10) + "," + str(view_height // 10)
        # bounds_str = str(bounds_arr[1][0] - bounds_arr[0][0]) + "," + str(bounds_arr[1][1] - bounds_arr[0][1])
        # if clickable:
        #     xpath = tree.getpath(node)
        #     # views_on_screen.add(xpath)
        #     views_on_screen.add(xpath + "#" + bounds_str)
        xpath = tree.getpath(node)
        # views_on_screen.add(xpath)
        if check_text_exclude(attribs["text"], xpath):
            all_text.append(attribs["text"])
        if clickable:
            exclude_flag1 = "RecyclerView" in xpath
            # exclude_flag2 = "ListView" in xpath and view_width < 540
            exclude_flag2 = "ListView" in xpath and attribs["package"] != "com.ichi2.anki"
            exclude_flag = exclude_flag1 or exclude_flag2
            cur_symbol = xpath + "#" + bounds_str
            if exclude_flag:
                if not check_contain(cur_symbol, clickable_views_on_screen):
                    clickable_views_on_screen.add(cur_symbol)
            else:
                clickable_views_on_screen.add(cur_symbol)
        views_on_screen.add(xpath + "#" + bounds_str)
    # if len(all_text) == 0:
    #     text_hash = 0
    # else:
    #     all_text_str = "#".join(all_text)
    #     text_hash = hash(all_text_str)
    # return views_on_screen, all_text
    return {"views_on_screen": views_on_screen, "all_text": all_text,
            "clickable_views_on_screen": clickable_views_on_screen}


def check_text_exclude(text_content: str, xpath: str):
    common_words = ["save", "add", "done", "ok", "next", "previous", "back"]
    # exclude_parents = ["RecyclerView"]
    exclude_parents = []
    clean_xpath = re.sub(r"\[\d+]", "", xpath)
    if text_content == None or len(text_content.strip()) == 0:
        return False
    if "helloworld" in text_content.lower():
        return False
    if "edittext" in xpath.split("/")[-1].lower():
        return False
    if text_content.lower() in common_words:
        return False
    for view_class in clean_xpath.split("/"):
        if view_class.split(".")[-1] in exclude_parents:
            return False
    return True


def check_contain(new_symbol, all_symbol):
    new_symbol2 = re.sub(r"\d", "*", new_symbol)
    all_symbol2 = set()
    for symbol in all_symbol:
        all_symbol2.add(re.sub(r"\d", "*", symbol))
    return new_symbol2 in all_symbol2


def compare_rec_app(rec_json, app_xml):
    a = extract_views_on_screen(rec_json)
    xml_page = open(app_xml, "r", encoding="UTF_8").read()
    b = extract_views_on_xml_screen(xml_page)
    b.setdefault("activity", a["activity"])
    print("######################")
    print(len(a["clickable_views_on_screen"]))
    print(len(b["clickable_views_on_screen"]))
    print(len(a["views_on_screen"]))
    print(len(b["views_on_screen"]))
    print(get_state_sim(a, b, prinf_diff=True))


if __name__ == '__main__':
    # extract_views_on_screen(1)
    # merge_same_state("D:/PycharmProjects/StepReproduceVer2/Data/RecDroid/DroidBotRes/19.Pix-Art-share_s", debug=True)
    id2state, state2id, state2detail, id2path = merge_same_state(
        "../Data/MyData/DroidBotRes/1_TeamNewPipe-NewPipe-7825",
        debug=True)
    # print("id2path", id2path)
    # merge_same_state("../Data/AndroR2/DroidBotRes/253", debug=True)
    # a = extract_views_on_screen(
    #     r"../Data/RecDroid2/DroidBotRes/31.tago/states/state_2022-08-24_120810.json")
    # print(a["all_text"])
    # print(len(a["clickable_views_on_screen"]))
    # xml_page = open("../Temp/mydata_30_1.xml", "r", encoding="UTF_8").read()
    # b = extract_views_on_xml_screen(xml_page)
    # b.setdefault("activity", a["activity"])
    # print(b["all_text"])
    # print(len(b["clickable_views_on_screen"]))
    # print(get_state_sim(a, b, prinf_diff=True))
    # b = extract_views_on_screen(
    #     r"../Data/MyData/DroidBotRes/5_fennifith-Alarmio-47/states/state_2022-06-04_153220.json")
    # print(b["all_text"])
    # print(len(b["clickable_views_on_screen"]))
    # print(get_state_sim(a, b, prinf_diff=True))
    # c = extract_views_on_screen(
    #     r"../Data/RecDroid2/DroidBotRes/30.Anki-Android\states\state_2022-06-17_182347.json")
    # xml_page = open("../Temp/recdroid_30_1.xml", "r", encoding="UTF_8").read()
    # a = extract_views_on_xml_screen(xml_page)
    # print(len(a["clickable_views_on_screen"]))
    # a.setdefault("activity", c["activity"])
    # xml_page = open("../Temp/recdroid_30_2.xml", "r", encoding="UTF_8").read()
    # b = extract_views_on_xml_screen(xml_page)
    # b.setdefault("activity", c["activity"])
    # print(len(b["clickable_views_on_screen"]))
    # print(check_state_is_same(a, b, print_diff=True))
    # print("c:", len(c["clickable_views_on_screen"]))
    # print(get_state_sim(b, c, prinf_diff=False))
    # d = extract_views_on_screen(
    #     r"../Data/RecDroid2/DroidBotRes/30.Anki-Android\states\state_2022-06-17_182409.json")
    # print("d:", len(d["clickable_views_on_screen"]))
    # print(get_state_sim(b, d, prinf_diff=False))
    # xml_page = open(
    #     "../Data/MyData/DroidBotRes/16_7LPdWcaW-GrowTracker-Android-87/appium_state/state_11_0614_210404.xml", "r",
    #     encoding="UTF_8").read()
    # a = extract_views_on_xml_screen(xml_page)
    # a.setdefault("activity", "123")
    # print(a["all_text"])
    # xml_page = open(
    #     "../Data/MyData/DroidBotRes/16_7LPdWcaW-GrowTracker-Android-87/appium_state/state_12_0614_174626.xml", "r",
    #     encoding="UTF_8").read()
    # b = extract_views_on_xml_screen(xml_page)
    # b.setdefault("activity", "123")
    # c = extract_views_on_screen(
    #     r"../Data/MyData/DroidBotRes/16_7LPdWcaW-GrowTracker-Android-87/states/state_2022-06-13_172049.json")
    # c["activity"] = "123"
    # print(b["all_text"])
    # print(len(a["clickable_views_on_screen"]))
    # print(len(b["clickable_views_on_screen"]))
    # print(len(c["clickable_views_on_screen"]))
    # print(get_state_sim(a, b, prinf_diff=True))
    # print(get_state_sim(a, c, prinf_diff=False))
    # print(get_state_sim(b, c, prinf_diff=False))
    #
    # aaa = re.sub(r"\[\d+]", "", "uhdiuh[12][0duihu[1]")
    # print(aaa)
    # a = extract_views_on_screen(
    #     r"../Data/RecDroid/DroidBotRes/23.news_s/states/state_2022-08-23_184303.json")
    # b = extract_views_on_screen(
    #     r"../Data/RecDroid/DroidBotRes/23.news_s/states/state_2022-08-23_184323.json")
    # print(get_state_sim(a, b, prinf_diff=True))
    # xml_page = open(
    #     "../Temp/mydata_25_1.xml", "r",
    #     encoding="UTF_8").read()
    # b = extract_views_on_xml_screen(xml_page)
    # b.setdefault("activity", a["activity"])
    # print(get_state_sim(a, b, prinf_diff=True))

    # xml_page = open(r"../Temp/recdroid_25_1.xml", "r", encoding="UTF_8").read()
    # a = extract_views_on_xml_screen(xml_page)
    # a.setdefault("activity", "123")
    # print(a["clickable_views_on_screen"])
    # b = extract_views_on_screen(r"../Data/RecDroid2/DroidBotRes/25.dagger_refresh/states/state_2022-08-05_165029.json")
    # b["activity"]="123"
    # print(b["clickable_views_on_screen"])
    # print(get_state_sim(a, b, prinf_diff=True))
    compare_rec_app(r"../Data/MyData/DroidBotRes/1_TeamNewPipe-NewPipe-7825/states/state_2022-06-02_214937.json",
                    r"../Temp/mydata_1_1.xml")
