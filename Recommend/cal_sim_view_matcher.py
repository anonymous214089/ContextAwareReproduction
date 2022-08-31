import os
import re
import shutil
from UTG.view import View
from UTG.states_and_views import StateViewInfo
from Recommend.util import get_str_sim, get_view_refer_name, SimpleWordAnalyser
import pandas as pd
import numpy as np


def get_reproduce_step(step_file):
    step_list = {}
    step_lines = open(step_file, "r").readlines()
    for step_idx, step_line in enumerate(step_lines):
        if len(step_line.strip()) == 0:
            continue
        cur_type = step_line.strip().split("#")[0]
        step_targets = step_line.strip().split("#")[1].lower()
        step_list.setdefault("step_" + str(step_idx), {"type": cur_type, "step_targets": step_targets})
    return step_list


def get_prj_list():
    prj_dict = {}
    for prj in os.listdir("../Data/RecDroid/apk"):
        prj_dict.setdefault(int(prj.split(".")[0]), prj.replace(".apk", ""))
    return prj_dict


def get_sim_old(step_type, step_target, view_key, view_info: View):
    # print(view_info)
    confirm_button = ["save", "add", "create", "done", "ok", "confirm"]
    view_type = view_info.view_class
    refer_name = get_view_refer_name(view_info)
    if refer_name == "" or refer_name == "none":
        return -1
    if step_type == "input" and view_type != "android.widget.EditText":
        return -1
    if step_type == "long-click" and "_LongClick" not in view_key:
        return -1
    cover_radio, edit_radio, exceed_punish = get_str_sim(step_target.lower(), refer_name)
    sim = cover_radio - 0.3 * edit_radio - 0.1 * exceed_punish
    if sim < 0.5 and refer_name.lower() in confirm_button:
        sim += 0.1
    return sim


def get_sim(step_line: str, view_key: str, view_info: View, matcher_score: float, word_analyser: SimpleWordAnalyser,
            in_top3: bool):
    # case 1: matcher give a confident match score, direct return
    # if matcher_score > 0.7:
    #     return matcher_score
    view_type = view_info.view_class
    refer_name = get_view_refer_name(view_info)
    # if "state_4" in view_key:
    #     print(refer_name)
    clean_res = word_analyser.clean_irrelevant_word(step_line)
    step_unsplit_set = set(clean_res["relevant_words"])
    step_split_set = set(clean_res["relevant_words_split"])
    # view_set = set(refer_name.split())
    clean_refer_name = re.sub("[^a-z0-9]", " ", refer_name.lower())
    clean_refer_name = re.sub("\s+", " ", clean_refer_name).strip()
    view_set = set(clean_refer_name.split())
    # view_set = word_analyser.get_stem_res(refer_name)
    cover_rate = get_cover_rate(step_unsplit_set, step_split_set, view_set)
    if matcher_score > 0.7:
        if cover_rate > 0.9 and cover_rate > matcher_score:
            return cover_rate
        else:
            return matcher_score
    if view_type[-8:].lower() != "edittext":
        # case 2: for button, return cover rate as the sim
        return cover_rate
    else:
        # case 3:
        if in_top3:
            return min(1.0, 0.2 + 2 * cover_rate)
        else:
            return cover_rate


def get_cover_rate(step_unsplit_set: set, step_split_set: set, view_set: set):
    inter_unsplit = step_unsplit_set.intersection(view_set)
    inter_split = step_split_set.intersection(view_set)
    view_cover_step_unsplit = len(inter_unsplit) / len(step_unsplit_set) if len(step_unsplit_set) > 0 else 0
    view_cover_step_split = len(inter_split) / len(step_split_set) if len(step_split_set) > 0 else 0
    step_cover_view_unsplit = len(inter_unsplit) / len(view_set) if len(view_set) > 0 else 0
    step_cover_view_split = len(inter_split) / len(view_set) if len(view_set) > 0 else 0
    if view_cover_step_unsplit > view_cover_step_split:
        view_cover_step = view_cover_step_unsplit
        step_word_count = len(step_unsplit_set)
    else:
        view_cover_step = view_cover_step_split
        step_word_count = len(step_split_set)
    step_cover_view = max(step_cover_view_unsplit, step_cover_view_split)
    view_word_count = len(view_set)
    view_step_rate = view_word_count / step_word_count if step_word_count > 0 else 999
    step_view_rate = step_word_count / view_word_count if view_word_count > 0 else 999

    if step_word_count >= 4:
        vcs_weight = 0.6
    else:
        vcs_weight = 1
    if view_word_count >= 4:
        scv_weight = 0.6
    else:
        scv_weight = 1
    view_cover_step_weight = vcs_weight / (vcs_weight + scv_weight)
    step_cover_view_weight = scv_weight / (vcs_weight + scv_weight)
    cover_rate = view_cover_step_weight * view_cover_step + step_cover_view_weight * step_cover_view
    if view_step_rate < 5 and step_view_rate < 5:
        return cover_rate
    else:
        return 0


def get_step_view_sim(state_view_info, all_score):
    match_thres = 0.7
    match_step2view = {}
    match_view2step = {}
    match_need_explore = {}
    all_sim = {}
    input_contents = []

    views = state_view_info.views
    word_analyser = SimpleWordAnalyser()
    all_score = all_score.tolist()
    step_lines = open("../Temp/current_views/val_desc.tsv", "r", encoding="UTF-8").readlines()
    step_lines = [l.strip().split("\t")[1] for l in step_lines if len(l.strip()) > 0]
    step_view_score = {i: [] for i in range(len(step_lines))}
    cur_data = pd.read_csv("../Temp/current_views/val_data.csv")
    idx2key = open("../Temp/current_views/key_map.tsv", "r", encoding="UTF-8").readlines()
    idx2key = [l.split("\t")[1].strip() for l in idx2key if len(l.strip()) > 0]
    for idx, row in cur_data.iterrows():
        step_view_score[row["desc_idx"]].append(all_score[idx])

    for step_idx, step_line in enumerate(step_lines):
        step_key = "step_" + str(step_idx)
        cur_step_sim_res = {}
        cur_match_views = []
        cur_score = np.array(step_view_score[step_idx])
        sim_scores_argsort = np.argsort(-cur_score)
        sim_scores_argsort = sim_scores_argsort.tolist()
        # max_range = min(3, cur_score.shape[0])
        match_top3 = sim_scores_argsort[:3]
        analyse_res = word_analyser.clean_irrelevant_word(step_line)
        for w in analyse_res["maybe_input_contents"]:
            clean_w = re.sub("[^a-zA-Z0-9]", "", w)
            if w not in input_contents and (len(clean_w) > 0 or w == " "):
                input_contents.append(w)

        if step_line.split()[0] in ["exit", "close"]:
            next_line = step_lines[step_idx + 1]
            if "open" in next_line or "restart" in next_line:
                state_view_info.add_restart_views()
                for view_key in views.keys():
                    if "KEY#RESTART" in view_key:
                        print("%%% match restart view_key:", view_key)
                        print("%%% match restart dst_state:", views[view_key].dst_state)
                        if view_key not in match_view2step.keys():
                            match_view2step.setdefault(view_key, {step_key: 0.9})
                        else:
                            match_view2step[view_key].setdefault(step_key, 0.9)
                        cur_step_sim_res.setdefault(view_key, {"sim": 0.9, "src_state": views[view_key].src_state,
                                                               "dst_state": views[view_key].dst_state})
                        cur_match_views.append(view_key)
                        match_step2view.setdefault(step_key,
                                                   {"match_count": len(cur_match_views), "views": cur_match_views})
                        all_sim.setdefault(step_key, cur_step_sim_res)
                continue

        for view_idx, view_key in enumerate(idx2key):
            view_info = views[view_key]
            matcher_score = cur_score[view_idx]
            is_in_top3 = view_idx in match_top3
            smooth_sim = get_sim(step_line, view_key, view_info, matcher_score, word_analyser, is_in_top3)
            relevant_words = word_analyser.clean_irrelevant_word(step_line)
            if is_in_top3:
                match_flag = smooth_sim >= match_thres
                cur_sim = smooth_sim
            else:
                match_flag = smooth_sim >= 0.75
                cur_sim = smooth_sim if match_flag else matcher_score
                view_refer_name = get_view_refer_name(view_info)
                if smooth_sim >= 0.75:
                    print("+match ori query:", step_line)
                    print("+match relevant words:", relevant_words)
                    print("+match view refer name:", view_refer_name)
                    print("+match dst:", view_info.dst_state)
                    # print("+match smooth_sim:", smooth_sim)
            view_refer_name = get_view_refer_name(view_info)
            # if "attach" in view_refer_name and "attach" in step_line:
            #     print(view_key)
            #     print(smooth_sim)
            #     print(matcher_score)
            # if "sync" in view_refer_name.lower():
            #     print(view_key)
            #     print(smooth_sim)
            #     print(matcher_score)
            # if "cardview" in step_line and "cardview" in view_refer_name:
            #     print("$$$ ori query:", step_line)
            #     # print("$$$ smooth_sim:", smooth_sim)
            #     print("$$$ is_in_top3:", is_in_top3)
            #     relevant_words = word_analyser.clean_irrelevant_word(step_line)
            #     print("$$$ relevant words:", relevant_words)
            #     view_refer_name = get_view_refer_name(view_info)
            #     print("$$$ view refer name:", view_refer_name)
            #     print("$$$ dst:", view_info.dst_state)
            cur_step_sim_res.setdefault(view_key, {"sim": cur_sim, "src_state": view_info.src_state,
                                                   "dst_state": view_info.dst_state})
            if match_flag:
                if view_info.dst_state != "unknown":
                    print("ori query:", step_line)
                    relevant_words = word_analyser.clean_irrelevant_word(step_line)
                    print("relevant words:", relevant_words)
                    view_refer_name = get_view_refer_name(view_info)
                    print("view refer name:", view_refer_name)
                    print("view_key:", view_key)
                    print("dst_state:", view_info.dst_state)
                    print("dst_state_not_sure:", view_info.dst_state_not_sure)
                    # print("matcher_score:", matcher_score)
                    # print("sim:", smooth_sim)
                    print("#" * 20)
                    cur_match_views.append(view_key)
                    if view_key not in match_view2step.keys():
                        match_view2step.setdefault(view_key, {step_key: cur_sim})
                    else:
                        match_view2step[view_key].setdefault(step_key, cur_sim)
                else:
                    print("$match but unknown$ ori query:", step_line)
                    relevant_words = word_analyser.clean_irrelevant_word(step_line)
                    print("$match but unknown$ relevant words:", relevant_words)
                    view_refer_name = get_view_refer_name(view_info)
                    print("$match but unknown$ view refer name:", view_refer_name)
                    print("$match but unknown$ view_key:", view_key)
                    # print("$match but unknown$ matcher_score:", matcher_score)
                    # print("$match but unknown$ sim:", smooth_sim)
                    print("#" * 20)
                    if view_info.src_state not in match_need_explore.keys():
                        match_need_explore.setdefault(view_info.src_state, [view_key])
                    else:
                        match_need_explore[view_info.src_state].append(view_key)
                if view_info.dst_state_not_sure:
                    if view_info.src_state not in match_need_explore.keys():
                        match_need_explore.setdefault(view_info.src_state, [view_key])
                    else:
                        match_need_explore[view_info.src_state].append(view_key)
        if len(analyse_res["relevant_words"]) == 1 and analyse_res["relevant_words"][
            0] == 'back' and "go" not in step_line:
            for view_key in views.keys():
                if "KEY#BACK" in view_key:
                    print("%%% match back ori query:", step_line)
                    print("%%% match back relevant words:", analyse_res)
                    print("%%% match back view_key:", view_key)
                    print("%%% match back dst_state:", views[view_key].dst_state)
                    if views[view_key].dst_state != "unknown":
                        if view_key not in match_view2step.keys():
                            match_view2step.setdefault(view_key, {step_key: 0.9})
                        else:
                            match_view2step[view_key].setdefault(step_key, 0.9)
                        cur_step_sim_res.setdefault(view_key, {"sim": 0.9, "src_state": views[view_key].src_state,
                                                               "dst_state": views[view_key].dst_state})
                        cur_match_views.append(view_key)
                    else:
                        if views[view_key].src_state not in match_need_explore.keys():
                            match_need_explore.setdefault(views[view_key].src_state, [view_key])
                        else:
                            match_need_explore[views[view_key].src_state].append(view_key)
        # if ('rotate' in analyse_res["relevant_words"] or 'rotation' in analyse_res["relevant_words"]) and len(
        #         cur_match_views) == 0:
        if ('rotate' in analyse_res["relevant_words"] or 'rotation' in analyse_res["relevant_words"]):
            state_view_info.add_rotate_views()
            for view_key in views.keys():
                if "KEY#ROTATE" in view_key:
                    print("%%% match rotate ori query:", step_line)
                    print("%%% match rotate relevant words:", analyse_res)
                    print("%%% match rotate view_key:", view_key)
                    print("%%% match rotate dst_state:", views[view_key].dst_state)
                    if views[view_key].dst_state != "unknown":
                        if view_key not in match_view2step.keys():
                            match_view2step.setdefault(view_key, {step_key: 0.9})
                        else:
                            match_view2step[view_key].setdefault(step_key, 0.9)
                        cur_step_sim_res.setdefault(view_key, {"sim": 0.9, "src_state": views[view_key].src_state,
                                                               "dst_state": views[view_key].dst_state})
                        cur_match_views.append(view_key)
                    else:
                        if views[view_key].src_state not in match_need_explore.keys():
                            match_need_explore.setdefault(views[view_key].src_state, [view_key])
                        else:
                            match_need_explore[views[view_key].src_state].append(view_key)
        match_step2view.setdefault(step_key, {"match_count": len(cur_match_views), "views": cur_match_views})
        all_sim.setdefault(step_key, cur_step_sim_res)
    print(input_contents)
    match_meta = {"match_step2view": match_step2view, "match_view2step": match_view2step, "all_sim": all_sim,
                  "match_need_explore": match_need_explore, "input_contents": input_contents}
    return match_meta

    # for step_key, step_info in step_list.items():
    #     cur_step_sim_res = {}
    #     cur_match_views = []
    #     step_type = step_info["type"]
    #     step_target = step_info["step_targets"]
    #     if step_type == "input":
    #         input_contents.append(step_target)
    #
    #     for view_key, view_info in views.items():
    #
    #         cur_sim = get_sim(step_type, step_target, view_key, view_info)
    #         cur_step_sim_res.setdefault(view_key, {"sim": cur_sim, "src_state": view_info.src_state,
    #                                                "dst_state": view_info.dst_state})
    #         if cur_sim > match_thres:
    #             if view_info.dst_state != "unknown":
    #                 print("###", step_key, "match:", cur_sim)
    #                 print("\tmatch target:", step_target)
    #                 print("\tmatch view:", get_view_refer_name(view_info))
    #                 print("\tview key:", view_key)
    #                 print("\tdst state:", view_info.dst_state)
    #                 # print(view_info.child_text)
    #                 cur_match_views.append(view_key)
    #                 if view_key not in match_view2step.keys():
    #                     match_view2step.setdefault(view_key, {step_key: cur_sim})
    #                 else:
    #                     match_view2step[view_key].setdefault(step_key, cur_sim)
    #             else:
    #                 if view_info.src_state not in match_need_explore.keys():
    #                     match_need_explore.setdefault(view_info.src_state, [view_key])
    #                 else:
    #                     match_need_explore[view_info.src_state].append(view_key)
    #             if view_info.dst_state_not_sure:
    #                 if view_info.src_state not in match_need_explore.keys():
    #                     match_need_explore.setdefault(view_info.src_state, [view_key])
    #                 else:
    #                     match_need_explore[view_info.src_state].append(view_key)


def get_view_sim(prj_dir: str, state_view_info: StateViewInfo, all_score):
    match_meta = get_step_view_sim(state_view_info, all_score)
    return match_meta


if __name__ == '__main__':
    word_analyser = SimpleWordAnalyser()
    refer_name = "Map in a recycler/cardview Layout"
    clean_res = word_analyser.clean_irrelevant_word('"Map in a recycler / cardview Layout"')
    step_unsplit_set = set(clean_res["relevant_words"])
    print(step_unsplit_set)
    step_split_set = set(clean_res["relevant_words_split"])
    print(step_split_set)
    # view_set = word_analyser.get_stem_res(refer_name)
    clean_refer_name = re.sub("[^a-z0-9]", " ", refer_name.lower())
    clean_refer_name = re.sub("\s+", " ", clean_refer_name).strip()
    view_set = set(clean_refer_name.split())
    print(view_set)
    cover_rate = get_cover_rate(step_unsplit_set, step_split_set, view_set)
    print(cover_rate)
