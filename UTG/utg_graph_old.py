import json
import re
import os
from UTG.screen_analyse import check_same_state, merge_same_state



class UTGGraph:
    def __init__(self, prj_dir):
        # Build UTG
        droidbot_res_str = open(os.path.join(prj_dir, "utg.js"), "r").readlines()
        droidbot_res_str = "".join(droidbot_res_str[1:])
        droidbot_res = json.loads(droidbot_res_str)
        nodes = droidbot_res["nodes"]
        edges = droidbot_res["edges"]
        id2cluster, cluster2id, state_clusters, id2detail = merge_same_state(prj_dir)
        inf = 114514
        self.idx2id = [node["id"] for node in nodes]
        self.id2idx = {nid: idx for idx, nid in enumerate(self.idx2id)}
        self.idx2cluster = [cluster for cluster in cluster2id.keys()]
        self.cluster2idx = {cluster: idx for idx, cluster in enumerate(self.idx2cluster)}
        self.all_clusters = set(self.cluster2idx.keys())
        # self.n = len(self.idx2id)
        self.n = len(cluster2id.keys())
        self.graph = [[inf for _ in range(self.n)] for _ in range(self.n)]
        self.parents = [[i for _ in range(self.n)] for i in range(self.n)]
        self.transition = {}
        for i in range(self.n):
            self.graph[i][i] = 0
        self.graph[0][1] = 1
        self.graph[1][0] = 1
        self.exclude_node = []
        for node in nodes:
            if "com.mumu." in node["package"]:
                self.exclude_node.append(node["id"])
        for edge in edges:
            # self.graph[self.id2idx[edge["from"]]][self.id2idx[edge["to"]]] = 1
            ori_transition = edge["id"]
            start_cluster = id2cluster[ori_transition.split("-->")[0]]
            end_cluster = id2cluster[ori_transition.split("-->")[1]]
            cur_transition = start_cluster + "-->" + end_cluster
            for event in edge["events"]:
                cur_event_str = event["event_str"]
                match_view_str = re.match(r".*?, view=([0-9a-f]+)\(.*?", cur_event_str, re.M | re.I)
                if match_view_str:
                    view_str = match_view_str.group(1)
                    if cur_transition not in self.transition.keys():
                        self.transition.setdefault(cur_transition, [view_str])
                    else:
                        self.transition[cur_transition].append(view_str)
                    # self.graph[self.id2idx[edge["from"]]][self.id2idx[edge["to"]]] = 1
                    self.graph[self.cluster2idx[start_cluster]][self.cluster2idx[end_cluster]] = 1
                elif cur_event_str[:8] == "KeyEvent":
                    click_key = cur_event_str.split("name=")[-1][:-1]
                    if cur_transition not in self.transition.keys():
                        self.transition.setdefault(cur_transition, ["KEY#" + click_key])
                    else:
                        self.transition[cur_transition].append("KEY#" + click_key)
                    # self.graph[self.id2idx[edge["from"]]][self.id2idx[edge["to"]]] = 1
                    self.graph[self.cluster2idx[start_cluster]][self.cluster2idx[end_cluster]] = 1
        # for same_state in same_states:
        #     cur_transition = same_state[0] + "-->" + same_state[1]
        #     if cur_transition not in self.transition.keys():
        #         self.transition.setdefault(cur_transition, ["SAME_STATE"])
        #         self.graph[self.id2idx[same_state[0]]][self.id2idx[same_state[1]]] = 1
        for k in range(self.n):
            for i in range(self.n):
                for j in range(self.n):
                    if self.graph[i][k] + self.graph[k][j] < self.graph[i][j]:
                        self.graph[i][j] = self.graph[i][k] + self.graph[k][j]
                        self.parents[i][j] = self.parents[k][j]

        self.dis_dict = {}
        for i in range(self.n):
            # self.dis_dict.setdefault(self.idx2id[i], {})
            self.dis_dict.setdefault(self.idx2cluster[i], {})
            for j in range(self.n):
                self.dis_dict[self.idx2cluster[i]].setdefault(self.idx2cluster[j], self.graph[i][j])
        # for i in range(self.n):
        #     for j in range(self.n):
        #         print('Path({}-->{}): '.format(i, j), end='')
        #         path_arr = []
        #         get_path(i, j, parents)
        #         print(' cost:', G[i][j])

    # def get_dis(self, src_screen, dst_screen):
    #     if src_screen not in self.dis_dict.keys() or dst_screen not in self.dis_dict[src_screen].keys():
    #         return 114514
    #     else:
    #         return self.dis_dict[src_screen][dst_screen]

    def get_dis(self, src_cluster, dst_cluster):
        if src_cluster not in self.dis_dict.keys() or dst_cluster not in self.dis_dict[src_cluster].keys():
            return 114514
        else:
            return self.dis_dict[src_cluster][dst_cluster]

    def get_path_recursion(self, src_idx, dst_idx, path_arr):
        if src_idx != dst_idx:
            self.get_path_recursion(src_idx, self.parents[src_idx][dst_idx], path_arr)
        # print(j, end='-->')
        # path_arr.append(self.idx2id[dst_idx])
        path_arr.append(self.idx2cluster[dst_idx])

    # def get_path(self, src_screen, dst_screen):
    #     path_arr = []
    #     src_id = self.id2idx[src_screen]
    #     dst_id = self.id2idx[dst_screen]
    #     self.get_path_recursion(src_id, dst_id, path_arr)
    #     return path_arr

    def get_path(self, src_cluster, dst_cluster):
        path_arr = []
        src_id = self.cluster2idx[src_cluster]
        dst_id = self.cluster2idx[dst_cluster]
        self.get_path_recursion(src_id, dst_id, path_arr)
        return path_arr

    # def get_transition_view(self, src_screen, dst_screen):
    #     transition_id = src_screen + "-->" + dst_screen
    #     if transition_id not in self.transition.keys():
    #         return []
    #     else:
    #         return self.transition[transition_id]

    def get_transition_view(self, src_cluster, dst_cluster):
        transition_id = src_cluster + "-->" + dst_cluster
        if transition_id not in self.transition.keys():
            return []
        else:
            return self.transition[transition_id]

    def get_path_by_seq_old(self, screen_seq_ori):
        screen_seq = screen_seq_ori.copy()
        full_path = []
        for state_idx in range(len(screen_seq) - 1):
            if screen_seq[state_idx + 1] == "":
                screen_seq[state_idx + 1] = screen_seq[state_idx]
            sub_path = self.get_path(screen_seq[state_idx], screen_seq[state_idx + 1])
            if len(sub_path) <= 1:
                continue
            if len(full_path) > 0 and full_path[-1] == sub_path[0]:
                full_path.extend(sub_path[1:])
            else:
                full_path.extend(sub_path)
        return full_path

    def get_path_by_seq(self, step_screen_ori):
        step_screen = []
        for t in step_screen_ori:
            step_screen.append(t.copy())
        full_path = []
        full_action = []
        last_step_screen = ""
        for step_idx in range(1, len(step_screen)):
            # print("#" * 20)
            # print("step_idx:", step_idx, step_screen[step_idx])
            if step_screen[step_idx]["pre"] == "":
                step_screen[step_idx]["pre"] = step_screen[step_idx - 1]["post"]
                step_screen[step_idx]["post"] = step_screen[step_idx - 1]["post"]
            elif step_screen[step_idx]["post"] == "":
                step_screen[step_idx]["post"] = step_screen[step_idx]["pre"]
                # step_screen[step_idx]["post"] = last_step_screen
            print("# from:", step_screen[step_idx - 1]["post"])
            print("# to(pre):", step_screen[step_idx]["pre"])
            print("# to(post):", step_screen[step_idx]["post"])
            print("# full_path", len(full_path), ":", full_path)
            # sub_path = self.get_path(step_screen[step_idx - 1]["post"], step_screen[step_idx]["pre"])
            if step_screen[step_idx - 1]["post"] != step_screen[step_idx]["pre"]:
                sub_path = self.get_path(step_screen[step_idx - 1]["post"], step_screen[step_idx]["pre"])
                if len(full_path) == 0:
                    sub_path = sub_path[1:]
                if len(full_path) > 0 and full_path[-1] == sub_path[0]:
                    full_path.extend(sub_path[1:])
                else:
                    full_path.extend(sub_path)
                for i in range(len(sub_path) - 1):
                    cur_transition = sub_path[i] + "-->" + sub_path[i + 1]
                    if cur_transition not in self.transition:
                        full_action.append([sub_path[i], "Can Not Find"])
                    else:
                        if self.transition[cur_transition][0] == "SAME_STATE":
                            continue
                        trans_action = self.transition[cur_transition][0]
                        for taction in self.transition[cur_transition]:
                            if "KEY#" not in taction:
                                trans_action = taction
                        full_action.append([sub_path[i], trans_action, self.transition[cur_transition]])
            if step_screen[step_idx]["action"] != "":
                full_action.append([step_screen[step_idx]["pre"], step_screen[step_idx]["action"]])
            if step_screen[step_idx]["pre"] != step_screen[step_idx]["post"] and step_screen[step_idx]["post"] != "":
                full_path.append(step_screen[step_idx]["post"])
                last_step_screen = step_screen[step_idx]["post"]
        for a in full_action:
            print(a)
        return full_path, full_action

    def get_transfer_path(self, src_cluster, dst_cluster):
        sub_path = self.get_path(src_cluster, dst_cluster)
        transfer_views = []
        for i in range(len(sub_path) - 1):
            cur_transition = sub_path[i] + "-->" + sub_path[i + 1]
            if cur_transition not in self.transition:
                # transition_views.append([sub_path[i], "Can Not Find"])
                transfer_views.append("Can Not Find")
            else:
                trans_action = self.transition[cur_transition][0]
                for taction in self.transition[cur_transition]:
                    if "KEY#" not in taction:
                        trans_action = taction
                transfer_views.append((sub_path[i] + "#" + trans_action, sub_path[i], sub_path[i + 1]))
        return transfer_views


def test_graph():
    utg_file_path = "../Data/RecDroid/DroidBotRes/1.newsblur_s/utg.js"
    utg_file = open(utg_file_path, "r", encoding="UTF-8")
    utg = json.loads(utg_file.read().replace("var utg = ", "").strip())
    idx2id = [node["id"] for node in utg["nodes"]]
    id2idx = {nid: idx for idx, nid in enumerate(idx2id)}
    idx_edges = []
    for edge in utg["edges"]:
        src_idx = str(id2idx[edge["from"]])
        dst_idx = str(id2idx[edge["to"]])
        idx_edges.append((src_idx, dst_idx))
    graph = UTGGraph("../Data/RecDroid/DroidBotRes/1.newsblur_s/")
    for node1 in idx2id:
        for node2 in idx2id:
            print(graph.get_dis(node1, node2))
            print(graph.get_path(node1, node2))


if __name__ == '__main__':
    test_graph()
