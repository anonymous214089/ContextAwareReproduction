from UTG.states_and_views import StateViewInfo
# from Recommend.cal_sim_heuristicly import get_view_sim
from Recommend.cal_sim_view_matcher import get_view_sim
# from Recommend.path_ranking_graph import PathRankingGraph
from Recommend.dynamic_programming2 import PathRankingGraph
from RunOnEmu.execute import Executor
from RunOnEmu.controller import EmuRunner
from RunOnEmu.util import get_andror2_apk_info
from Model.train import ViewMatcher
import os
from Explore.explore_view import Explorer
import subprocess
import re

def get_prj_dict():
    prj_dict = {}
    for prj in os.listdir("../Data/AndroR2/apk"):
        prj = re.sub(r"[^0-9]", "", prj)
        prj_dict.setdefault(int(prj.split(".")[0]), prj.replace(".apk", ""))
    return prj_dict


def run(execute_prj_idx: int):
    recdroid_apk_info = get_andror2_apk_info()
    pkg_name = recdroid_apk_info[execute_prj_idx]["appPackage"]
    print("#" * 8 + "Stage 1: init emu and STG from droidbot" + "#" * 8)
    prj_dict = get_prj_dict()
    prj_name = prj_dict[execute_prj_idx]
    prj_dir = "../Data/AndroR2/DroidBotRes/" + prj_name
    state_view_info = StateViewInfo(prj_dir)
    controller = EmuRunner(recdroid_apk_info[execute_prj_idx], state_view_info)
    # controller = ""
    executor = Executor(controller, state_view_info)
    view_matcher = ViewMatcher("../Model/out/training_stsbenchmark-2022-03-14_09-38-31")

    log_path = "../Temp/log/log_out.txt"
    log_file = open(log_path, "w")
    log_file.close()
    log_cmd = "adb -s emulator-5554 logcat"
    with open("../Temp/log/log_out.txt", "wb") as out, open("log_err.txt", "wb") as err:
        subprocess.Popen(log_cmd, stdout=out, stderr=err)

    run_turn = 1
    while run_turn <= 999:
        print("#" * 8 + "Stage 2: match steps and views" + "#" * 8)
        # match_meta = get_view_sim(prj_dir, state_view_info)

        all_score = view_matcher.predict_on_recdroid("../Temp/current_views")
        match_meta = get_view_sim(prj_dir, state_view_info, all_score)
        _ = input("continue?")

        print("#" * 8 + "Stage 3: recommend an execute path" + "#" * 8)
        path_ranking = PathRankingGraph(match_meta, state_view_info)
        recommend_meta = path_ranking.start_ranking()
        _ = input("continue?")

        print("#" * 8 + "Stage 4: execute the recommend path on emu" + "#" * 8)
        # final_state = execute(recommend_meta, controller, state_view_info)
        final_state, visit_states = executor.execute(recommend_meta)
        # if final_state == "state_0" or final_state == "emu_launcher":
        #     break
        success = input("continue?")

        if success.strip() == "q":
            break

        print("#" * 8 + "Stage 5: explore views" + "#" * 8)
        explorer = Explorer(controller, state_view_info, match_meta, visit_states, recommend_meta)
        explorer.explore_view()


if __name__ == '__main__':
    excute_prj_idx = 23
    run(excute_prj_idx)
    # a = [1, 2, 3]
    # b = {"a": 1, "b": "c"}
    # print(type(a) == type(list()))
    # print(type(b) == type(list()))
    #
    # print(type(a) == type(dict()))
    # print(type(b) == type(dict()))
    # print(isinstance(a, (list, dict)))
    # print(isinstance(b, (list, dict)))
    # print(isinstance("123", (list, dict)))