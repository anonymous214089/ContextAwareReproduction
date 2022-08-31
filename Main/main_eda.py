from UTG.states_and_views import StateViewInfo
# from Recommend.cal_sim_heuristicly import get_view_sim
from Recommend.cal_sim_view_matcher import get_view_sim
# from Recommend.path_ranking_graph import PathRankingGraph
from Recommend.dynamic_programming2 import PathRankingGraph
from RunOnEmu.execute import Executor
from RunOnEmu.controller import EmuRunner
from RunOnEmu.util import check_crash
from Model.train import ViewMatcher
import os
import subprocess
# from Explore.explore_view import Explorer
from Explore.explore_view2 import Explorer
import time
import json


def get_recdroid_apk_info():
    ori_apk_info = json.load(open("../Data/eda/activity.txt", "r"))
    apk_info = {}
    for apk_name, info in ori_apk_info.items():
        apk_info.setdefault(int(apk_name.split(".")[0]),
                            {"appPackage": info["appPackage"], "appActivity": info["appActivity"][0]})
    return apk_info


def get_prj_dict():
    prj_dict = {}
    for prj in os.listdir("../Data/eda/apk"):
        prj_dict.setdefault(int(prj.split(".")[0]), prj.replace(".apk", ""))
    return prj_dict


def reinstall_app(app_name, app_pkg):
    if "'" in app_name:
        return
    if "28." in app_name or "29." in app_name :
        return
    uninstall_cmd = "adb -s emulator-5554 uninstall " + app_pkg
    os.system(uninstall_cmd)
    time.sleep(1)
    install_cmd = "adb -s emulator-5554 install ../Data/eda/apk/" + app_name + ".apk"
    os.system(install_cmd)


def replace_eda_report(rate, app_name, report_idx):
    print(rate, app_name, report_idx)
    in_cont = open("../Data/eda/eda_report/" + str(rate) + "/" + app_name + "/" + str(report_idx) + ".txt", "r").read()
    print(in_cont)
    output_file = open("../Data/eda/oriReport/" + app_name + ".txt", "w")
    output_file.write(in_cont)


def run(execute_prj_idx: int):
    recdroid_apk_info = get_recdroid_apk_info()
    pkg_name = recdroid_apk_info[execute_prj_idx]["appPackage"]
    prj_dict = get_prj_dict()
    prj_name = prj_dict[execute_prj_idx]
    replace_eda_report(eda_rate, prj_name, report_idx)
    prj_dir = "../Data/eda/DroidBotRes/" + prj_name
    reinstall_app(prj_name, pkg_name)
    print("#" * 8 + "Stage 1: init emu and STG from droidbot" + "#" * 8)
    state_view_info = StateViewInfo(prj_dir)
    if execute_prj_idx == 28 or execute_prj_idx == 29:
        controller = EmuRunner(recdroid_apk_info[execute_prj_idx], state_view_info, app_reset=False)
    else:
        controller = EmuRunner(recdroid_apk_info[execute_prj_idx], state_view_info)
    # controller = ""
    executor = Executor(controller, state_view_info)
    view_matcher = ViewMatcher("../Model/out/training_stsbenchmark-2022-06-22_20-27-54")

    log_path = "../Temp/log/log_out.txt"
    log_file = open(log_path, "w")
    log_file.close()
    os.system("adb -s emulator-5554 logcat -c")
    log_cmd = "adb -s emulator-5554 logcat"
    log_out = open("../Temp/log/log_out.txt", "wb")
    log_err = open("../Temp/log/log_err.txt", "wb")
    log_proc = subprocess.Popen(log_cmd, stdout=log_out, stderr=log_err, shell=True)
    run_turn = 1
    start_time = time.time()
    print("$ start")
    predict_time = 0
    while run_turn <= 999:
        print("#" * 8 + "Stage 2: match steps and views" + "#" * 8)
        # match_meta = get_view_sim(prj_dir, state_view_info)
        pred_start_time = time.time()
        all_score = view_matcher.predict_on_recdroid("../Temp/current_views")
        match_meta = get_view_sim(prj_dir, state_view_info, all_score)
        pred_end_time = time.time()
        predict_time += pred_end_time - pred_start_time
        # _ = input("continue?")

        print("#" * 8 + "Stage 3: recommend an execute path" + "#" * 8)
        path_ranking = PathRankingGraph(match_meta, state_view_info)
        recommend_meta = path_ranking.start_ranking()
        # _ = input("continue?")

        print("#" * 8 + "Stage 4: execute the recommend path on emu" + "#" * 8)
        # final_state = execute(recommend_meta, controller, state_view_info)
        final_state, visit_states = executor.execute(recommend_meta)
        if final_state == "state_0" or final_state == "emu_launcher" or check_crash():
            break
        # success = input("continue?")
        #
        # if success.strip() == "q":


        #     break

        print("#" * 8 + "Stage 5: explore views" + "#" * 8)
        explorer = Explorer(controller, state_view_info, match_meta, visit_states, recommend_meta)
        explorer.explore_view()
        if check_crash():
            break
    end_time = time.time()
    print("use time:", end_time - start_time)
    print("predict_time:", predict_time)
    log_out.close()
    log_err.close()
    log_proc.terminate()


if __name__ == '__main__':
    eda_rate = 20
    report_idx = 3

    excute_prj_idx = 28
    run(excute_prj_idx)