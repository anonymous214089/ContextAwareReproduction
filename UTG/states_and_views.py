import os
import json
from UTG.screen_analyse3 import merge_same_state, extract_views_on_xml_screen, check_state_is_same, get_state_sim
from UTG.parse_layout_droidbot import parse_layout_droidbot
from UTG.parse_layout_appium import parse_layout_appium
from UTG.view import View
from UTG.state import State
import re
from Recommend.util import get_view_refer_name
import time
import shutil
import cv2
import pandas as pd
from Preprocess.preprocess_report2 import report_preprocess
import os


class StateViewInfo():
    def __init__(self, droidbot_res_dir: str):
        self.droidbot_res_dir = droidbot_res_dir
        droidbot_utg_str = open(os.path.join(droidbot_res_dir, "utg.js"), "r").readlines()
        droidbot_utg_str = "".join(droidbot_utg_str[1:])
        droidbot_utg = json.loads(droidbot_utg_str)
        self.droidbot_res_dir = droidbot_res_dir
        self.cur_apk_name = self.droidbot_res_dir.replace("\\", "/").split("/")[-1]
        self.nodes = droidbot_utg["nodes"]
        self.edges = droidbot_utg["edges"]
        self.id2state, self.state2id, self.state2detail, self.id2path = merge_same_state(droidbot_res_dir)
        # self.all_states = ["state_" + str(state_idx) for state_idx in range(len(self.state2id.keys()))]
        self.all_states = list(self.state2id.keys())
        self.state2idx = {state: idx for idx, state in enumerate(self.all_states)}
        self.view_str_transition = {state: {} for state in self.all_states}
        self.view_str_transition_long = {state: {} for state in self.all_states}
        self.view_xpath_transition = {state: {} for state in self.all_states}
        # self.transition = []
        self.transition = {}
        self.pre_state_map = {}
        self.exclude_node = []
        self.dis_dict = {}
        self.n = 0
        self.inf = 114514
        self.stg = []
        self.stg_parents = []

        self.views = {}
        self.states = {}
        self.new_find_state = []
        self.init_droidbot_stg()

    def init_droidbot_stg(self):
        find_views = set()
        for node in self.nodes:
            if "com.android.launcher" in node["package"]:
                self.exclude_node.append(node["id"])
        for edge in self.edges:
            ori_transition = edge["id"]
            if ori_transition.split("-->")[0] not in self.id2state.keys() or ori_transition.split("-->")[
                1] not in self.id2state.keys():
                continue
            start_state = self.id2state[ori_transition.split("-->")[0]]
            # if "9999" in start_state:
            #     start_state =
            end_state = self.id2state[ori_transition.split("-->")[1]]
            # if end_state == "state_0":
            #     continue
            if end_state != 0:
                if end_state not in self.pre_state_map.keys():
                    self.pre_state_map.setdefault(end_state, set())
                self.pre_state_map[end_state].add(start_state)

            for event in edge["events"]:
                cur_event_str = event["event_str"]
                match_view_str = re.match(r".*?, view=([0-9a-f]+)\(.*?", cur_event_str, re.M | re.I)
                if match_view_str:
                    if cur_event_str[:10] == "TouchEvent":
                        view_str = match_view_str.group(1)
                        if end_state != "state_0":
                            if view_str not in self.view_str_transition[start_state].keys():
                                self.view_str_transition[start_state].setdefault(view_str, [end_state])
                            elif end_state not in self.view_str_transition[start_state][view_str]:
                                self.view_str_transition[start_state][view_str].append(end_state)
                    elif cur_event_str[:14] == "LongTouchEvent":
                        view_str = match_view_str.group(1)
                        if end_state != "state_0":
                            if view_str not in self.view_str_transition_long[start_state].keys():
                                self.view_str_transition_long[start_state].setdefault(view_str, [end_state])
                            elif end_state not in self.view_str_transition_long[start_state][view_str]:
                                self.view_str_transition_long[start_state][view_str].append(end_state)
                elif cur_event_str[:8] == "KeyEvent":
                    screen_json_path = self.id2path[ori_transition.split("-->")[0]]
                    screen_img_path = screen_json_path.replace(".json", ".png").replace("state_", "screen_")
                    click_key = cur_event_str.split("name=")[-1][:-1]
                    click_symbol = start_state + "###KEY#" + click_key

                    if end_state not in self.view_xpath_transition[start_state].keys():
                        self.view_xpath_transition[start_state].setdefault(end_state, set())
                    self.view_xpath_transition[start_state][end_state].add(click_symbol)
                    # self.stg[self.state2idx[start_state]][self.state2idx[end_state]] = 1
                    # self.transition.append([self.state2idx[start_state], self.state2idx[end_state]])
                    self.transition.setdefault(click_symbol, [self.state2idx[start_state], self.state2idx[end_state]])
                    self.view_str_transition[start_state].setdefault("KEY#" + click_key, end_state)
                    fake_info = {"format": "system_key"}
                    system_key_view = View(fake_info)
                    system_key_view.view_class = "system_key"
                    system_key_view.view_type = "system_key"
                    system_key_view.src_state = start_state
                    system_key_view.img_path = screen_img_path
                    if end_state == "state_0":
                        system_key_view.dst_state = "unknown"
                    else:
                        system_key_view.dst_state = end_state
                    system_key_view.text = click_key
                    if "9999" not in start_state:
                        self.views.setdefault(click_symbol, system_key_view)

        for screen_id, ori_state_id in self.id2state.items():
            if "9999" in ori_state_id:
                state_id = ori_state_id.replace("9999", "")
            else:
                state_id = ori_state_id
            if state_id not in self.states.keys():
                cur_activity = self.state2detail[state_id]["activity"]
                new_state = State(state_id, cur_activity)
                self.states.setdefault(state_id, new_state)
            screen_json_path = self.id2path[screen_id]
            screen_img_path = screen_json_path.replace(".json", ".png").replace("state_", "screen_")
            clickable_views = parse_layout_droidbot(screen_json_path)
            has_edittext = False
            for view_symbol, view_info in clickable_views.items():
                if view_info["class"][-8:].lower() == "edittext":
                    has_edittext = True
                    break
            all_view_strs = [view_symbol.split("###")[0] for view_symbol in clickable_views.keys()]
            for view_symbol, view_info in clickable_views.items():
                # self.view_xpath_transition = []
                view_str = view_symbol.split("###")[0]
                if "9999" in ori_state_id:
                    view_key = state_id + "###" + view_info["xpath"] + "_Scroll" + screen_id[-4:]
                    # print("$$$", view_key)
                else:
                    view_key = state_id + "###" + view_info["xpath"]
                view_info.setdefault("img_path", screen_img_path)
                view_info.setdefault("format", "droidbot")
                view_info.setdefault("src_state", state_id)
                dst_state = "unknown"

                child_view_strs = view_info["child_view_strs"]
                child_dst_state = set()
                use_child_str = ""
                for child_view_str in child_view_strs:
                    if child_view_str not in self.view_str_transition[state_id].keys():
                        continue
                    child_view_dst_states = self.view_str_transition[state_id][child_view_str]
                    if len(child_view_dst_states) == 1:
                        child_view_dst_state = child_view_dst_states[0]
                        use_child_str = child_view_str
                        child_dst_state.add(child_view_dst_state)
                if len(child_dst_state) == 1:
                    child_dst_state = child_dst_state.pop()
                else:
                    child_dst_state = "unknown"

                if view_str in self.view_str_transition[state_id].keys():
                    if all_view_strs.count(view_str) > 1:
                        # print("same view_str", state_id, view_str, all_view_strs.count(view_str))
                        # if view_str == "7891e682ad8fed70b73800f9dcda73e3":
                        #     cur_bounds = view_info["bounds"]
                        #     if cur_bounds[0][0] > 850 and cur_bounds[1][0] < 1050:
                        #         dst_state = child_dst_state
                        #         dst_state_not_sure = True
                        if child_dst_state != "unknown":
                            # print("$$$ set by child dst state:", child_dst_state, use_child_str,
                            #       view_info["xpath"].split(".")[-1])
                            dst_state = child_dst_state
                            dst_state_not_sure = False
                        else:
                            dst_states = self.view_str_transition[state_id][view_str]
                            view_idx = int(view_symbol.split("###")[1])
                            if view_idx < len(dst_states):
                                dst_state = dst_states[view_idx]
                            else:
                                dst_state = dst_states[-1]
                            if view_str == "7891e682ad8fed70b73800f9dcda73e3":
                                # fix droidbot multi same id in Markor
                                cur_bounds = view_info["bounds"]
                                if cur_bounds[0][0] > 850 and cur_bounds[1][0] < 1050:
                                    dst_state = dst_states[-1]
                                else:
                                    dst_state = state_id
                                # print(cur_bounds, dst_state)
                            dst_state_not_sure = True
                    else:
                        dst_states = self.view_str_transition[state_id][view_str]
                        if len(dst_states) == 1:
                            dst_state_not_sure = False
                        else:
                            # print("### confuse:", view_str, dst_states)
                            dst_state_not_sure = True
                        dst_state = dst_states[0]
                    view_info.setdefault("dst_state", dst_state)
                    view_info.setdefault("dst_state_not_sure", dst_state_not_sure)
                    # self.transition.setdefault(view_key, [self.state2idx[state_id], self.state2idx[dst_state]])
                    # if dst_state not in self.view_xpath_transition[state_id].keys():
                    #     self.view_xpath_transition[state_id].setdefault(dst_state, set())
                    # self.view_xpath_transition[state_id][dst_state].add(view_key)
                else:
                    if view_info["class"][-8:].lower() == "edittext":
                        dst_state = state_id
                        dst_state_not_sure = False
                        view_info.setdefault("dst_state", state_id)
                        view_info.setdefault("dst_state_not_sure", dst_state_not_sure)
                        # if dst_state not in self.view_xpath_transition[state_id].keys():
                        #     self.view_xpath_transition[state_id].setdefault(dst_state, set())
                        # self.view_xpath_transition[state_id][dst_state].add(view_key)
                    else:
                        view_info.setdefault("dst_state", "unknown")
                        view_info.setdefault("dst_state_not_sure", False)
                new_view = View(view_info)
                is_confirm_button = self.check_is_confirm_button(new_view)
                if view_key not in self.views.keys():
                    if "_Scroll" not in view_key:
                        self.views.setdefault(view_key, new_view)
                        self.states[state_id].add_view(view_key, new_view)
                        find_views.add(str(new_view.get_view_hash()))
                        if state_id != dst_state and "state" in dst_state:
                            self.transition.setdefault(view_key, [self.state2idx[state_id], self.state2idx[dst_state]])
                        if "state" in dst_state:
                            if dst_state not in self.view_xpath_transition[state_id].keys():
                                self.view_xpath_transition[state_id].setdefault(dst_state, set())
                            self.view_xpath_transition[state_id][dst_state].add(view_key)
                    else:
                        cur_view_hash = str(new_view.get_view_hash())
                        # if state_id == "state_2":
                        #     print("new_view.view_type", new_view.view_type)
                        #     print("find hash:", cur_view_hash not in find_views)
                        if cur_view_hash not in find_views:
                            # print("add:", view_key)
                            self.views.setdefault(view_key, new_view)
                            self.states[state_id].add_view(view_key, new_view)
                            find_views.add(cur_view_hash)
                            if state_id != dst_state and "state" in dst_state:
                                self.transition.setdefault(view_key,
                                                           [self.state2idx[state_id], self.state2idx[dst_state]])
                            if "state" in dst_state:
                                if dst_state not in self.view_xpath_transition[state_id].keys():
                                    self.view_xpath_transition[state_id].setdefault(dst_state, set())
                                self.view_xpath_transition[state_id][dst_state].add(view_key)
                else:
                    if self.views[view_key].dst_state == "unknown" and dst_state != "unknown":
                        self.views[view_key].dst_state = dst_state
                # if state_id == "state_6":
                #     print("### view_key:", view_key)
                #     print("### dst_state:", dst_state)

                if view_info["long_clickable"] and view_info["class"][-8:].lower() != "edittext":
                    long_view_key = view_key + "_LongClick"
                    copy_view_info = {}
                    for k, v in view_info.items():
                        if isinstance(v, (list, dict)):
                            copy_view_info.setdefault(k, v.copy())
                        else:
                            copy_view_info.setdefault(k, v)
                    dst_state = "unknown"
                    dst_state_not_sure = False
                    if view_str in self.view_str_transition_long[state_id].keys():
                        dst_states = self.view_str_transition_long[state_id][view_str]
                        dst_state = dst_states[0]
                        if len(dst_states) == 1:
                            dst_state_not_sure = False
                        else:
                            dst_state_not_sure = True
                        if dst_state not in self.view_xpath_transition[state_id].keys():
                            self.view_xpath_transition[state_id].setdefault(dst_state, set())
                        self.view_xpath_transition[state_id][dst_state].add(long_view_key)
                        self.transition.setdefault(long_view_key, [self.state2idx[state_id], self.state2idx[dst_state]])
                    copy_view_info["dst_state"] = dst_state
                    copy_view_info["dst_state_not_sure"] = dst_state_not_sure
                    new_long_view = View(copy_view_info)
                    if long_view_key not in self.views.keys():
                        self.views.setdefault(long_view_key, new_long_view)
                    self.states[state_id].add_view(long_view_key, new_long_view)
                    # print("long_click_view:", long_view_key, dst_state)
                    if long_view_key not in self.views.keys():
                        if "_Scroll" not in view_key:
                            self.views.setdefault(long_view_key, new_long_view)
                            self.states[state_id].add_view(long_view_key, new_long_view)
                            find_views.add(str(new_long_view.get_view_hash()))
                        else:
                            cur_view_hash = str(new_long_view.get_view_hash())
                            if cur_view_hash not in find_views:
                                self.views.setdefault(long_view_key, new_long_view)
                                self.states[state_id].add_view(long_view_key, new_long_view)
                                find_views.add(cur_view_hash)

                # for confirm button(e.g., create), fill info and click may direct different state
                view_class = view_info["class"]
                if is_confirm_button and has_edittext:
                    fill_info_view_key = view_key + "_FillInfo"
                    copy_view_info = {}
                    for k, v in view_info.items():
                        if isinstance(v, (list, dict)):
                            copy_view_info.setdefault(k, v.copy())
                        else:
                            copy_view_info.setdefault(k, v)
                    # copy_view_info["dst_state"] = "unknown"
                    copy_view_info["dst_state_not_sure"] = True
                    fill_info_view = View(copy_view_info)
                    if fill_info_view_key not in self.views.keys():
                        # print("find fill info view!", fill_info_view_key)
                        self.views.setdefault(fill_info_view_key, fill_info_view)
                    self.states[state_id].add_view(fill_info_view_key, fill_info_view)
        self.gen_stg()

    def gen_stg(self):
        self.dis_dict = {}
        self.n = len(self.all_states)
        self.stg = [[self.inf for _ in range(self.n)] for _ in range(self.n)]
        self.stg_parents = [[i for _ in range(self.n)] for i in range(self.n)]
        for i in range(self.n):
            self.stg[i][i] = 0
        self.stg[0][1] = 1
        self.stg[1][0] = 1
        # for view_key, (src_state, dst_state) in self.transition.items():
        #     self.stg[src_state][dst_state] = 1
        for view_key, view in self.views.items():
            if "state_" not in view.dst_state or view.src_state == "state_0":
                continue
            view_src_state = self.state2idx[view.src_state]
            view_dst_state = self.state2idx[view.dst_state]
            # if view_dst_state == self.state2idx["state_3"]:
            #     print("to state_3:", view_src_state)
            self.stg[view_src_state][view_dst_state] = 1
            # self.stg_parents[view_src_state][view_dst_state] = view_src_state
        for k in range(self.n):
            for i in range(self.n):
                for j in range(self.n):
                    if self.stg[i][k] + self.stg[k][j] < self.stg[i][j]:
                        self.stg[i][j] = self.stg[i][k] + self.stg[k][j]
                        self.stg_parents[i][j] = self.stg_parents[k][j]
        # print("self.stg_parents[2][3]:", self.stg_parents[2][3])
        # print(self.get_path("state_2", "state_3"))
        # print(self.get_path("state_1", "state_3"))
        for i in range(self.n):
            self.dis_dict.setdefault(self.all_states[i], {})
            for j in range(self.n):
                self.dis_dict[self.all_states[i]].setdefault(self.all_states[j], self.stg[i][j])
        self.export_all_views()

    def get_state_belong_old(self, current_activity: str, page_source: str, match_thres=0.6, print_sim=False):
        # views_on_screen, all_text = extract_views_on_xml_screen(page_source)
        # cur_state_detail = {"activity": current_activity, "views_on_screen": views_on_screen, "all_text": all_text}
        cur_state_detail = extract_views_on_xml_screen(page_source)
        crash_alert = False
        if len(cur_state_detail["all_text"]) == 2:
            match_crash = re.match(r"Unfortunately, .*? has stopped.", cur_state_detail["all_text"][0])
            if match_crash and cur_state_detail["all_text"][1] == "OK":
                crash_alert = True
                return "crash_page"
        cur_state_detail.setdefault("activity", current_activity)
        most_sim = -1
        most_sim_state = "unknown"
        for state_id, state_detail in self.state2detail.items():
            state_sim = get_state_sim(cur_state_detail, state_detail)
            if state_sim > most_sim:
                most_sim = state_sim
                most_sim_state = state_id
        if most_sim > match_thres:
            if print_sim:
                print("sim:", most_sim)
            return most_sim_state
        else:
            if "com.android.launcher" in current_activity or current_activity == ".Launcher":
                print("find Launcher:", current_activity)
                return "state_0"
            else:
                print("current_activity:", current_activity)
                print("most sim state:", most_sim_state, ", sim", most_sim)
                if most_sim_state in self.state2detail.keys():
                    most_sim_detail = self.state2detail[most_sim_state]
                    get_state_sim(cur_state_detail, most_sim_detail, prinf_diff=True)
                return "unknown"

    def get_state_belong(self, current_activity: str, page_source: str, match_thres=0.7, print_sim=False):
        cur_state_detail = extract_views_on_xml_screen(page_source)
        if len(cur_state_detail["all_text"]) == 2:
            match_crash = re.match(r"Unfortunately, .*? has stopped.", cur_state_detail["all_text"][0])
            if match_crash and cur_state_detail["all_text"][1] == "OK":
                return "crash_page"
        if "com.android.launcher" in current_activity or current_activity == ".Launcher":
            print("find Launcher:", current_activity)
            return "state_0"
        cur_state_detail.setdefault("activity", current_activity)
        match_states = []
        most_sim = -1
        most_sim_state = "unknown"
        for state_id, state_detail in self.state2detail.items():
            state_sim = get_state_sim(cur_state_detail, state_detail)
            if state_sim > most_sim:
                most_sim = state_sim
                most_sim_state = state_id
            if state_sim > match_thres:
                match_states.append([state_id, state_sim])
        if len(match_states) == 0:
            print("current_activity:", current_activity)
            print("most sim state:", most_sim_state, ", sim", most_sim)
            if most_sim_state in self.state2detail.keys():
                most_sim_detail = self.state2detail[most_sim_state]
                get_state_sim(cur_state_detail, most_sim_detail, prinf_diff=True)
            return "unknown"
        elif len(match_states) == 1:
            if print_sim:
                print("sim:", most_sim)
            return match_states[0][0]
        else:
            best_match_state = match_states[0][0]
            best_match_sim = -1
            cur_all_text = set(cur_state_detail["all_text"])
            cur_all_clickable = set(cur_state_detail["clickable_views_on_screen"])
            for (candi_state, candi_sim) in match_states:
                candi_all_text = self.state2detail[candi_state]["all_text"]
                candi_all_clickable = self.state2detail[candi_state]["clickable_views_on_screen"]
                text_union = cur_all_text.union(candi_all_text)
                text_inter = cur_all_text.intersection(candi_all_text)
                text_sim = len(text_inter) / len(text_union) if len(text_union) > 0 else 0
                view_union = cur_all_clickable.union(candi_all_clickable)
                view_inter = cur_all_clickable.intersection(candi_all_clickable)
                view_sim = len(view_inter) / len(view_union) if len(text_union) > 0 else 0
                candi_sum_sim = candi_sim + text_sim + view_sim
                if candi_sum_sim > best_match_sim:
                    best_match_state = candi_state
                    best_match_sim = candi_sum_sim
            if print_sim:
                print("candi match state:", [t[0] for t in match_states])
                print("best match state:", best_match_state)
                print("best_match_sim:", best_match_sim)
            return best_match_state

    def get_path(self, src_state, dst_state):
        path_arr = []
        if "state_" not in src_state or "state_" not in dst_state:
            return []
        src_id = self.state2idx[src_state]
        dst_id = self.state2idx[dst_state]
        self.get_path_recursion(src_id, dst_id, path_arr)
        return path_arr

    def get_path_recursion(self, src_idx, dst_idx, path_arr):
        if src_idx != dst_idx:
            self.get_path_recursion(src_idx, self.stg_parents[src_idx][dst_idx], path_arr)
        path_arr.append(self.all_states[dst_idx])

    def get_transfer_path(self, src_state, dst_state):
        temp_view_xpath_transition = {}
        for temp_view_key, temp_view in self.views.items():
            temp_src_state = temp_view.src_state
            temp_dst_state = temp_view.dst_state
            if "state_" not in temp_dst_state:
                continue
            if temp_src_state not in temp_view_xpath_transition.keys():
                temp_view_xpath_transition.setdefault(temp_src_state, {})
            if temp_dst_state not in temp_view_xpath_transition[temp_src_state].keys():
                temp_view_xpath_transition[temp_src_state].setdefault(temp_dst_state, [])
            temp_view_xpath_transition[temp_src_state][temp_dst_state].append(temp_view_key)
        sub_path = self.get_path(src_state, dst_state)
        # if src_state == "state_1" and dst_state == "state_4":
        #     print("transfer state path:", sub_path)
        transfer_views = []
        for i in range(len(sub_path) - 1):
            start_state = sub_path[i]
            end_state = sub_path[i + 1]
            # if end_state not in self.view_xpath_transition[start_state].keys():
            if start_state not in temp_view_xpath_transition.keys() or end_state not in temp_view_xpath_transition[
                start_state].keys():
                # transition_views.append([sub_path[i], "Can Not Find"])
                # transfer_views.append("Can Not Find")
                return []
            else:
                # trans_action = list(self.view_xpath_transition[start_state][end_state])[0]
                trans_action = list(temp_view_xpath_transition[start_state][end_state])[0]
                if end_state not in self.view_xpath_transition[start_state].keys():
                    return []
                for taction in self.view_xpath_transition[start_state][end_state]:
                    if "KEY#" not in taction:
                        trans_action = taction
                transfer_views.append([trans_action, start_state, end_state])
        return transfer_views

    def get_views_need_explore(self, given_state=None):
        views_need_explore = {}
        for view_symbol, view in self.views.items():
            explore_flag1 = (view.dst_state == "unknown")
            explore_flag2 = ("state" in view.dst_state and view.dst_state_not_sure)
            explore_flag3 = view.dst_state == "state_0" and "KEY#BACK" not in view_symbol
            # print("view.src_state", view.src_state, "dst_state", view.dst_state, "not sure", view.dst_state_not_sure)
            if view.src_state == "state_0":
                continue
            if not (explore_flag1 or explore_flag2 or explore_flag3):
                continue
            if given_state != None and view.src_state != given_state:
                continue
            if view.src_state not in views_need_explore.keys():
                views_need_explore.setdefault(view.src_state, [view_symbol])
            else:
                views_need_explore[view.src_state].append(view_symbol)
        return views_need_explore

    def get_dst_state_not_sure_views(self, given_state=None):
        views_need_explore = {}
        for view_symbol, view in self.views.items():
            explore_flag2 = ("state" in view.dst_state and view.dst_state_not_sure)
            if not explore_flag2:
                continue
            if given_state != None and view.src_state != given_state:
                continue
            if view.src_state not in views_need_explore.keys():
                views_need_explore.setdefault(view.src_state, [view_symbol])
            else:
                views_need_explore[view.src_state].append(view_symbol)
        return views_need_explore

    def update_view_transfer(self, view_key: str, new_dst_state: str):
        view = self.views[view_key]
        src_state = view.src_state
        old_dst_state = view.dst_state
        view.dst_state = new_dst_state
        view.dst_state_not_sure = False
        if old_dst_state in self.view_xpath_transition[src_state].keys():
            if view_key in self.view_xpath_transition[src_state][old_dst_state]:
                self.view_xpath_transition[src_state][old_dst_state].remove(view_key)
        if "state_" in new_dst_state:
            self.transition[view_key] = [self.state2idx[view.src_state], self.state2idx[new_dst_state]]
            if new_dst_state not in self.view_xpath_transition[src_state].keys():
                self.view_xpath_transition[src_state].setdefault(new_dst_state, set())
            self.view_xpath_transition[src_state][new_dst_state].add(view_key)
        else:
            if view_key in self.transition.keys():
                self.transition.pop(view_key)
        self.gen_stg()
        new_view = self.views[view_key]
        print("update res:", new_view.dst_state)

    def get_new_state_name(self):
        appium_state_dir = os.path.join(self.droidbot_res_dir, "appium_state")
        if not os.path.exists(appium_state_dir):
            os.mkdir(appium_state_dir)
        new_state_id = "state_" + str(len(self.all_states))
        time_str = time.strftime('%m%d_%H%M%S', time.localtime(time.time()))
        new_state_xml_path = os.path.join(appium_state_dir, new_state_id + "_" + time_str + ".xml")
        new_state_img_path = os.path.join(appium_state_dir, new_state_id + "_" + time_str + ".png")
        return new_state_id, new_state_xml_path, new_state_img_path

    def add_state(self, current_activity: str, page_source: str, view_key: str, new_state_id: str, new_state_xml_path,
                  new_state_img_path, has_find_views: set):
        # appium_state_dir = os.path.join(self.droidbot_res_dir, "appium_state")
        # if not os.path.exists(appium_state_dir):
        #     os.mkdir(appium_state_dir)
        # new_state_id = "state_" + str(len(self.all_states))
        # time_str = time.strftime('%m%d_%H%M%S', time.localtime(time.time()))
        # new_state_xml_path = os.path.join(appium_state_dir, new_state_id + "_" + time_str + ".xml")
        # new_state_img_path = os.path.join(appium_state_dir, new_state_id + "_" + time_str + ".png")
        with open(new_state_xml_path, "w", encoding="UTF-8") as f:
            f.write(page_source)

        new_state = State(new_state_id, current_activity)
        self.pre_state_map.setdefault(new_state_id, set())
        self.pre_state_map[new_state_id].add(view_key.split("###")[0])
        self.new_find_state.append(new_state_id)
        self.all_states.append(new_state_id)
        self.states.setdefault(new_state_id, new_state)
        # views_on_screen, all_text = extract_views_on_xml_screen(page_source)
        # cur_state_detail = {"activity": current_activity, "views_on_screen": views_on_screen, "all_text": all_text}
        cur_state_detail = extract_views_on_xml_screen(page_source)
        cur_state_detail.setdefault("activity", current_activity)
        self.state2detail.setdefault(new_state_id, cur_state_detail)
        self.state2idx = {state: idx for idx, state in enumerate(self.all_states)}
        transfer_view = self.views[view_key]
        transfer_view.dst_state = new_state_id
        transfer_view.dst_state_not_sure = False
        src_state = transfer_view.src_state
        # self.transition.append([src_state, new_state_id])
        # self.transition.setdefault(view_key, [src_state, new_state_id])
        self.transition.setdefault(view_key, [self.state2idx[src_state], self.state2idx[new_state_id]])
        self.view_xpath_transition[src_state].setdefault(new_state_id, set())
        self.view_xpath_transition[src_state][new_state_id].add(view_key)
        self.view_xpath_transition.setdefault(new_state_id, {})

        self.add_new_find_views(page_source, new_state_id, new_state_img_path, new_state, has_find_views)

        # clickable_views = parse_layout_appium(page_source)
        # has_edittext = False
        # for view_symbol, view_info in clickable_views.items():
        #     if view_info["class"][-8:].lower() == "edittext":
        #         has_edittext = True
        #         break
        # for view_xpath, view_info in clickable_views.items():
        #     is_confirm_button = False
        #     view_info.setdefault("img_path", new_state_img_path)
        #     view_info.setdefault("format", "droidbot")
        #     view_info.setdefault("src_state", new_state_id)
        #     if view_info["clickable"]:
        #         new_view_key = new_state_id + "###" + view_xpath
        #         if view_info["class"][-8:].lower() == "edittext":
        #             view_info.setdefault("dst_state", new_state_id)
        #             view_info.setdefault("dst_state_not_sure", False)
        #         else:
        #             view_info.setdefault("dst_state", "unknown")
        #             view_info.setdefault("dst_state_not_sure", False)
        #         new_view = View(view_info)
        #         is_confirm_button = self.check_is_confirm_button(new_view)
        #         if new_view_key not in self.views.keys():
        #             print("# find new view:", new_view_key)
        #             self.views.setdefault(new_view_key, new_view)
        #         new_state.add_view(new_view_key, new_view)
        #     if view_info["long_clickable"] and view_info["class"][-8:].lower() != "edittext":
        #         long_view_key = new_state_id + "###" + view_xpath + "_LongClick"
        #         copy_view_info = {}
        #         for k, v in view_info.items():
        #             if isinstance(v, (list, dict)):
        #                 copy_view_info.setdefault(k, v.copy())
        #             else:
        #                 copy_view_info.setdefault(k, v)
        #         copy_view_info["dst_state"] = "unknown"
        #         copy_view_info["dst_state_not_sure"] = False
        #         new_long_view = View(copy_view_info)
        #         if long_view_key not in self.views.keys():
        #             print("# find new long click view:", long_view_key)
        #             self.views.setdefault(long_view_key, new_long_view)
        #         new_state.add_view(long_view_key, new_long_view)
        #     view_class = view_info["class"]
        #     is_button = (view_class[-8:].lower() == "textview" or view_class[-6:].lower() == "button" or view_class[
        #                                                                                                  -6:].lower() == "layout")
        #     if is_confirm_button and has_edittext and is_button:
        #         fill_info_view_key = new_state_id + "###" + view_xpath + "_FillInfo"
        #         copy_view_info = {}
        #         for k, v in view_info.items():
        #             if isinstance(v, (list, dict)):
        #                 copy_view_info.setdefault(k, v.copy())
        #             else:
        #                 copy_view_info.setdefault(k, v)
        #         # copy_view_info["dst_state"] = "unknown"
        #         copy_view_info["dst_state_not_sure"] = True
        #         fill_info_view = View(copy_view_info)
        #         if fill_info_view_key not in self.views.keys():
        #             print("# find fill info view!", fill_info_view_key)
        #             self.views.setdefault(fill_info_view_key, fill_info_view)
        #         new_state.add_view(fill_info_view_key, fill_info_view)
        click_key = "BACK"
        click_symbol = new_state_id + "###KEY#" + click_key
        fake_info = {"format": "system_key"}
        system_key_view = View(fake_info)
        system_key_view.view_class = "system_key"
        system_key_view.view_type = "system_key"
        system_key_view.src_state = new_state_id
        system_key_view.img_path = new_state_img_path
        system_key_view.dst_state = "unknown"
        system_key_view.dst_state_not_sure = False
        system_key_view.text = click_key
        self.views.setdefault(click_symbol, system_key_view)
        new_state.add_view(click_symbol, system_key_view)
        self.gen_stg()
        return new_state_id

    def add_scroll_state(self, page_source: str, new_state_id, new_state_img_path, has_find_views: set):
        new_state = self.states[new_state_id]
        self.add_new_find_views(page_source, new_state_id, new_state_img_path, new_state, has_find_views,
                                is_scroll=True)
        return new_state_id

    def add_new_find_views(self, page_source, new_state_id: str, new_state_img_path: str, new_state: State,
                           has_find_views: set, is_scroll=False):
        clickable_views = parse_layout_appium(page_source)
        has_edittext = False
        for view_symbol, view_info in clickable_views.items():
            if view_info["class"][-8:].lower() == "edittext":
                has_edittext = True
                break
        for view_xpath, view_info in clickable_views.items():
            is_confirm_button = False
            view_info.setdefault("img_path", new_state_img_path)
            view_info.setdefault("format", "droidbot")
            view_info.setdefault("src_state", new_state_id)
            if view_info["clickable"]:
                new_view_key = new_state_id + "###" + view_xpath
                if view_info["class"][-8:].lower() == "edittext":
                    view_info.setdefault("dst_state", new_state_id)
                    view_info.setdefault("dst_state_not_sure", False)
                else:
                    view_info.setdefault("dst_state", "unknown")
                    view_info.setdefault("dst_state_not_sure", False)
                new_view = View(view_info)
                new_view_hash = str(new_view.get_view_hash())
                is_confirm_button = self.check_is_confirm_button(new_view)
                new_view_name = get_view_refer_name(new_view)
                if is_scroll:
                    new_view_key = new_view_key + "_Scroll" + str(new_view_hash)[:4]
                if new_view_key not in self.views.keys() and new_view_hash not in has_find_views:
                    print("# find new view:", new_view_name, new_view_key.split(".")[-1])
                    self.views.setdefault(new_view_key, new_view)
                    new_state.add_view(new_view_key, new_view)
                    has_find_views.add(new_view_hash)
            if view_info["long_clickable"] and view_info["class"][-8:].lower() != "edittext":
                long_view_key = new_state_id + "###" + view_xpath + "_LongClick"
                if is_scroll:
                    long_view_key = long_view_key + "_Scroll"
                copy_view_info = {}
                for k, v in view_info.items():
                    if isinstance(v, (list, dict)):
                        copy_view_info.setdefault(k, v.copy())
                    else:
                        copy_view_info.setdefault(k, v)
                copy_view_info["dst_state"] = "unknown"
                copy_view_info["dst_state_not_sure"] = False
                new_long_view = View(copy_view_info)
                new_long_view_hash = str(new_long_view.get_view_hash()) + "_LongClick"
                long_view_name = get_view_refer_name(new_long_view)
                if long_view_key not in self.views.keys() and new_long_view_hash not in has_find_views:
                    print("# find new long click view:", long_view_name, long_view_key.split(".")[-1])
                    self.views.setdefault(long_view_key, new_long_view)
                    new_state.add_view(long_view_key, new_long_view)
                    has_find_views.add(new_long_view_hash)
            view_class = view_info["class"]
            is_button = view_class[-8:].lower() == "textview" or view_class[-6:].lower() == "button"
            is_button = is_button or view_class[-6:].lower() == "layout"
            if is_confirm_button and has_edittext and is_button:
                fill_info_view_key = new_state_id + "###" + view_xpath + "_FillInfo"
                if is_scroll:
                    fill_info_view_key = fill_info_view_key + "_Scroll"
                copy_view_info = {}
                for k, v in view_info.items():
                    if isinstance(v, (list, dict)):
                        copy_view_info.setdefault(k, v.copy())
                    else:
                        copy_view_info.setdefault(k, v)
                # copy_view_info["dst_state"] = "unknown"
                copy_view_info["dst_state_not_sure"] = True
                fill_info_view = View(copy_view_info)
                fill_info_view_hash = str(fill_info_view.get_view_hash()) + "_FillInfo"
                fill_info_name = get_view_refer_name(fill_info_view)
                if fill_info_view_key not in self.views.keys() and fill_info_view_hash not in has_find_views:
                    print("# find fill info view!", fill_info_name, fill_info_view_key.split(".")[-1])
                    self.views.setdefault(fill_info_view_key, fill_info_view)
                    new_state.add_view(fill_info_view_key, fill_info_view)
                    has_find_views.add(fill_info_view_hash)


    def check_is_confirm_button(self, view: View, debug=False):
        confirm_button = ["save", "add", "create", "done", "ok", "confirm", "sign", "next", "unlock", "setup", "search",
                          "login"]
        confirm_button = set(confirm_button)
        confirm_words = ["log in"]
        refer_name = get_view_refer_name(view).lower()
        view_class = view.view_class
        refer_name_words = set(refer_name.split())
        is_confirm_button = len(refer_name_words.intersection(confirm_button)) > 0 or refer_name in confirm_words
        is_button = view_class[-8:].lower() == "textview" or (view_class[-6:].lower() in ["button", "layout"])
        view_bounds = view.bounds
        view_centerx = (view_bounds[0][0] + view_bounds[1][0]) / 2
        view_centery = (view_bounds[0][1] + view_bounds[1][1]) / 2
        # if view.src_state == "state_4" and view.process_sibling_text == "add new plant":
        #     print(view.process_sibling_text)
        #     print(view.process_sibling_text == "add new plant")
        #     return True
        if view.process_sibling_text == "add new plant":
            return True
        if view_centerx < 250 and view_centery < 150:
            return False
        if debug:
            print("refer_name:", refer_name)
            print("refer_name_words:", refer_name_words)
            print("intersection:", len(refer_name_words.intersection(confirm_button)))
        return is_confirm_button and is_button

    def export_all_views(self):
        export_dir = "../Temp/current_views"
        if not os.path.exists(export_dir):
            os.mkdir(export_dir)
        img_dir = os.path.join(export_dir, "image")
        if os.path.exists(img_dir):
            shutil.rmtree(img_dir)
        os.mkdir(img_dir)
        view_keys = [k for k in self.views.keys() if "KEY#" not in k]
        view_keys_lines = [str(idx) + "\t" + key for idx, key in enumerate(view_keys)]
        key_map_file = open(os.path.join(export_dir, "key_map.tsv"), "w", encoding="UTF-8")
        key_map_file.write("\n".join(view_keys_lines))
        key_map_file.close()
        view_strs = []
        for idx, key in enumerate(view_keys):
            cur_view = self.views[key]
            view_strs.append(str(cur_view))
            screen_img_path = cur_view.img_path
            view_bounds = cur_view.bounds
            screen_img = cv2.imread(screen_img_path)
            view_img = screen_img[view_bounds[0][1]:view_bounds[1][1], view_bounds[0][0]:view_bounds[1][0]]
            save_path = os.path.join(img_dir, str(idx) + ".png")
            cv2.imwrite(save_path, view_img)

        views_file = open(os.path.join(export_dir, "val_views.tsv"), "w", encoding="UTF-8")
        views_lines = [str(idx) + "\t" + view_str for idx, view_str in enumerate(view_strs)]
        views_file.write("\n".join(views_lines))
        views_file.close()

        # use report have been preprocessed by me
        # step_dir = self.droidbot_res_dir.replace("\\", "/").split("DroidBotRes")[0] + "report/"
        # step_file = open(step_dir + self.cur_apk_name + ".txt", "r")
        # step_lines = [l.strip() for l in step_file.readlines() if len(l.strip()) > 0]
        # desc_file = open(os.path.join(export_dir, "val_desc.tsv"), "w")
        # desc_file.write("\n".join(step_lines))
        # desc_file.close()

        # use auto preprocess
        report_dir = self.droidbot_res_dir.replace("\\", "/").split("DroidBotRes")[0] + "oriReport/"
        ori_report_path = report_dir + self.cur_apk_name + ".txt"
        desc_file_path = os.path.join(export_dir, "val_desc.tsv")
        step_lines = report_preprocess(ori_report_path, desc_file_path)

        pred_data = {"desc_idx": [], "view_idx": [], "label": [], "image": []}
        for step_idx in range(len(step_lines)):
            for view_idx in range(len(view_keys)):
                pred_data["desc_idx"].append(step_idx)
                pred_data["view_idx"].append(view_idx)
                pred_data["label"].append(1.0)
                img_path = os.path.join(img_dir, str(view_idx) + ".png")
                pred_data["image"].append(img_path)
        pred_df = pd.DataFrame(pred_data)
        pred_df.to_csv(os.path.join(export_dir, "val_data.csv"), index=False)

    def add_rotate_views(self):
        print("all state:", self.states.keys())
        for start_state in self.states.keys():
            if start_state == "state_0":
                continue
            cur_activity = self.states[start_state].activity
            if cur_activity == "IntroActivity":
                continue
            click_key = "ROTATE"
            click_symbol = start_state + "###KEY#" + click_key
            fake_info = {"format": "system_key"}
            system_key_view = View(fake_info)
            system_key_view.view_class = "system_key"
            system_key_view.view_type = "system_key"
            system_key_view.src_state = start_state
            system_key_view.dst_state = "state_0"
            system_key_view.dst_state_not_sure = False
            system_key_view.text = click_key
            self.views.setdefault(click_symbol, system_key_view)

    def add_restart_views(self):
        for start_state in self.states.keys():
            click_key = "RESTART"
            click_symbol = start_state + "###KEY#" + click_key
            fake_info = {"format": "system_key"}
            system_key_view = View(fake_info)
            system_key_view.view_class = "system_key"
            system_key_view.view_type = "system_key"
            system_key_view.src_state = start_state
            system_key_view.dst_state = "state_1"
            system_key_view.dst_state_not_sure = False
            system_key_view.text = click_key
            self.views.setdefault(click_symbol, system_key_view)

    def get_relevant_states(self, target_states: set):
        relevant_states = set()
        state_queue = list(target_states)
        while len(state_queue) != 0:
            cur_state = state_queue.pop()
            if cur_state in relevant_states:
                continue
            relevant_states.add(cur_state)
            if cur_state == "state_1" or cur_state not in self.pre_state_map.keys():
                continue
            pre_states = self.pre_state_map[cur_state]
            for pre_state in pre_states:
                if pre_state not in relevant_states:
                    relevant_states.add(pre_state)
                    state_queue.append(pre_state)
        return relevant_states

    def export_crash_steps(self, crash_click_views):
        export_dir = "../Temp/crash_steps"
        if os.path.exists(export_dir):
            shutil.rmtree(export_dir)
            os.mkdir(export_dir)
        for idx, key in enumerate(crash_click_views):
            cur_view = self.views[key]
            screen_img_path = cur_view.img_path
            view_bounds = cur_view.bounds
            if os.path.exists(screen_img_path):
                screen_img = cv2.imread(screen_img_path)
                if "KEY#" in key:
                    point_1 = (180, 1800)
                    point_2 = (290, 1910)
                else:
                    point_1 = (view_bounds[0][0], view_bounds[0][1])
                    point_2 = (view_bounds[1][0], view_bounds[1][1])
                rect_screen_img = cv2.rectangle(screen_img, point_1, point_2, (0, 255, 0), 2)
                save_path = os.path.join(export_dir, str(idx + 1) + ".png")
                cv2.imwrite(save_path, rect_screen_img)
            else:
                print("can't find image path:", screen_img_path)


if __name__ == '__main__':
    # a = StateViewInfo("../Data/RecDroid/DroidBotRes/1.newsblur_s")
    # print(time.strftime('%m%d_%H%M%S', time.localtime(time.time())))
    a = [[1, 2], [3, 4], [5, 6], [7, 8]]
    for (candi_state, candi_sim) in a:
        print(candi_state, candi_sim)
