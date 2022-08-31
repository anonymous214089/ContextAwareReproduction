from RunOnEmu.controller import EmuRunner
from ExtractOperation.match_droidbot import match_consider_state
from RunOnEmu.util import get_recdroid_apk_info
from ExtractOperation.screen_analyse import get_cluster_belong
from Recommend.recommend_excute_path import get_excute_views
from RunOnEmu.finishing_operation import Explorer
from Recommend.path_ranking_graph import PathRankingGraph


def execute():
    # 7 24
    execute_prj = 1
    recdroid_apk_info = get_recdroid_apk_info()
    # actions, cluster2id, id2detail = match_consider_state(execute_prj)
    # match_res = match_consider_state(execute_prj)

    view_sim_res = get_excute_views(execute_prj)

    path_ranking = PathRankingGraph(view_sim_res)
    recommend_paths = path_ranking.start_explore()
    recommend_path = recommend_paths[0][0]
    click_view_path = recommend_path.view_path

    controller = EmuRunner(recdroid_apk_info[execute_prj], view_sim_res)
    explorer = Explorer(controller, view_sim_res)
    # click_given_path(controller, explorer, view_sim_res)
    click_given_path2(controller, explorer, view_sim_res, click_view_path)

    # while True:
    #     a = input("get page")
    #     current_activity, page_source = runner.get_page_info()
    #     print(page_source)
    #     save_file = open("save_xml.xml", "w")
    #     save_file.write(page_source)
    #     print(get_cluster_belong(current_activity, page_source, view_sim_res["cluster2id"], view_sim_res["id2detail"]))


def click_given_path(controller: EmuRunner, explorer: Explorer, view_sim_res: dict):
    step_view_info = view_sim_res["step_view_info"]
    step_idxs = list(step_view_info.keys())
    step_idxs.sort()
    for step_idx in step_idxs:
        # print(step_view_info[step_idx])
        if step_view_info[step_idx]["may_match"] == 0:
            print("may match a wrong view, skip")
            continue
        target_view = step_view_info[step_idx]["view"]
        cur_cluster = controller.get_current_state()
        controller.detect_edittext_and_fill()
        if cur_cluster != target_view["src_cluster"]:
            transfer_views = view_sim_res["UTG"].get_transfer_path(cur_cluster, target_view["src_cluster"])
            for (transfer_view_key, from_cluster, to_cluster) in transfer_views:
                try_time = 0
                print(transfer_view_key)
                while try_time < 3:
                    before_cluster = controller.get_current_state()
                    if before_cluster == from_cluster:
                        print("start match")
                    if "KEY#" in transfer_view_key:
                        controller.click_back()
                    else:
                        print("123")
                        transfer_view = controller.view_sim_res["all_views_short_dict"][transfer_view_key]
                        print("456")
                        controller.click_view(transfer_view)
                        print("789")
                    after_cluster = controller.get_current_state()
                    if after_cluster == to_cluster:
                        print("transfer done match")
                        controller.detect_edittext_and_fill()
                        break
                    else:
                        try_time += 1
        print("click target_view:", target_view)
        controller.click_view(target_view)
    explorer.do_explore()


def click_given_path2(controller: EmuRunner, explorer: Explorer, view_sim_res: dict, click_view_path: list):
    step_view_info = view_sim_res["step_view_info"]
    step_idxs = list(step_view_info.keys())
    step_idxs.sort()
    for click_view in click_view_path:
        view_cluster = click_view.split("###")[0]
        view_xpath = click_view.split("###")[1]
        # print(step_view_info[step_idx])
        cur_cluster = controller.get_current_state()
        if view_cluster != cur_cluster:
            print("cluster not match, expect:", view_cluster, ", get:", cur_cluster)
            break
        controller.detect_edittext_and_fill()
        print("click target_view:", view_xpath)
        controller.click_view_by_xpath(view_xpath)
    explorer.do_explore()

if __name__ == '__main__':
    execute()