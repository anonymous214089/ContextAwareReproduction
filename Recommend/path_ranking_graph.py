from UTG.states_and_views import StateViewInfo
from Recommend.util import get_view_refer_name

step_punish = 0.3
unmatch_scale = 0.3
finish_scale = 2
create_reward = 1

class PathRankingGraph():
    def __init__(self, match_meta: dict, state_view_info: StateViewInfo):
        self.max_revisit_times = 5
        self.state_view_info = state_view_info
        self.match_step2view = match_meta["match_step2view"]
        self.match_view2step = match_meta["match_view2step"]
        self.input_contents = match_meta["input_contents"]
        self.all_sim = match_meta["all_sim"]
        self.all_states = state_view_info.all_states
        self.all_views = state_view_info.views
        self.view_xpath_transition = state_view_info.view_xpath_transition
        # print(self.view_xpath_transition)
        # print(state_view_info.view_str_transition)
        self.visited_view = set()
        self.all_transition = {state_id: {} for state_id in self.all_states}

        for view_key, view in self.all_views.items():
            if view.dst_state != "unknown":
                self.all_transition[view.src_state].setdefault(view_key, view.dst_state)

        for view_key in self.all_transition["state_3"]:
            view = state_view_info.views[view_key]
            print("#", self.all_transition["state_3"][view_key], get_view_refer_name(view))
            print(view_key)

        # for src_state in self.view_xpath_transition.keys():
        #     for dst_state in self.view_xpath_transition[src_state].keys():
        #         for view_key in self.view_xpath_transition[src_state][dst_state]:
        #             if "KEY#BACK" in view_key:
        #                 self.all_transition[src_state].setdefault(view_key, dst_state)

        # if len(self.all_transition["state_1"]) > 1 and "state_1###KEY#BACK" in self.all_transition["state_1"].keys():
        #     self.all_transition["state_1"].pop("state_1###KEY#BACK")

        # for src_state in self.view_xpath_transition.keys():
        #     for dst_state in self.view_xpath_transition[src_state].keys():
        #         for view_key in self.view_xpath_transition[src_state][dst_state]:
        #             self.all_transition[src_state].setdefault(view_key, dst_state)

        self.max_goal = 0
        for step_idx, step_match_info in self.match_step2view.items():
            if step_match_info["match_count"] > 0:
                self.max_goal += 1
        print("self.max_goal:", self.max_goal)
        self.all_state_nodes = {}
        self.finish_info = {"finish_count": 0, "finish_paths": []}
        self.all_path_info = []
        self.graph_meta = {"all_state_nodes": self.all_state_nodes, "all_transition": self.all_transition,
                           "max_goal": self.max_goal, "all_states": self.all_states, "finish_info": self.finish_info,
                           "match_step2view": self.match_step2view, "match_view2step": self.match_view2step,
                           "all_sim": self.all_sim, "max_revisit_times": self.max_revisit_times,
                           "all_views": self.all_views, "all_path_info": self.all_path_info,
                           "view_xpath_transition": self.view_xpath_transition, "state_view_info": self.state_view_info}
        for state_id in self.all_states:
            for visit_time in range(self.max_revisit_times):
                cur_node_key = state_id + "###" + str(visit_time + 1)
                cur_state_node = StateNode(state_id, visit_time + 1, self.graph_meta)
                if state_id.split("_")[-1] == "1" and visit_time == 0:
                    init_path = Path(self.graph_meta)
                    init_path.state_path.append(state_id)
                    init_path.visited_state_times[state_id] = 1
                    cur_state_node.add_path(init_path)
                self.all_state_nodes.setdefault(cur_node_key, cur_state_node)

    def start_ranking(self):
        expand_queue = [["state_1###1", 0]]
        expand_times = 0
        while len(expand_queue) != 0:
            if expand_times >= 1000:
                break
            if self.finish_info["finish_count"] >= 1000:
                self.finish_info["finish_paths"].sort(key=lambda x: -x[1])
                break
            expand_queue.sort(key=lambda x: -x[1])
            expand_info = expand_queue.pop(0)
            expand_node = expand_info[0]
            new_expand_list = self.all_state_nodes[expand_node].expand()
            # expand_queue.extend(new_expand_list)
            for new_expand_info in new_expand_list:
                in_queue = False
                for old_expand_info in expand_queue:
                    if old_expand_info[0] == new_expand_info[0] and new_expand_info[1] > old_expand_info[1]:
                        old_expand_info[1] = new_expand_info[1]
                        in_queue = True
                        break
                if not in_queue:
                    expand_queue.append(new_expand_info)
            # print("expand_times: " + str(expand_times), ", expand node:", expand_node, ", count:", len(new_expand_list))
            expand_times += 1
            # a = input("expand_times: " + str(expand_times))
        print("path graph explore finish")
        if self.finish_info["finish_count"] > 0:
            self.finish_info["finish_paths"].sort(key=lambda x: -x[1])
            for (finish_path, score) in self.finish_info["finish_paths"]:
                state_path_str = "-".join(finish_path.state_path)
                print("path " + state_path_str + " finished, score:", finish_path.get_score())
                print(finish_path.get_refer_name_str())
                print(finish_path.is_step_finish)
                break
            recommend_meta = {"recommend_paths": self.finish_info["finish_paths"], "input_contents": self.input_contents}
            # return self.finish_info["finish_paths"]
            return recommend_meta
        else:
            self.all_path_info.sort(key=lambda x: -x[1])
            find_path = self.all_path_info[0][0]
            state_path_str = "-".join(find_path.state_path)
            print("find path " + state_path_str + ", score:", find_path.get_score())
            print(find_path.get_refer_name_str())
            recommend_meta = {"recommend_paths": self.all_path_info[:1], "input_contents": self.input_contents}
            # return self.all_path_info[:1]
            return recommend_meta



class Path():
    def __init__(self, graph_meta: dict):
        self.graph_meta = graph_meta
        self.all_states = graph_meta["all_states"]
        self.all_transition = graph_meta["all_transition"]
        self.match_step2view = graph_meta["match_step2view"]
        self.match_view2step = graph_meta["match_view2step"]
        self.state_view_info = graph_meta["state_view_info"]
        self.all_sim = graph_meta["all_sim"]
        self.all_views = graph_meta["all_views"]
        self.is_step_finish = [0 for _ in range(len(self.match_step2view.keys()))]
        self.view_path = []
        self.state_path = []
        self.visited_state_times = {}
        self.step_score = []
        self.create_score = []
        self.path_score = 0
        for state_id in self.all_states:
            self.visited_state_times.setdefault(state_id, 0)

    def update_path(self):
        confirm_button = ["save", "add", "create", "done", "ok", "confirm", "sign"]
        confirm_button = set(confirm_button)
        refer_name_path = []
        for path_idx, view_key in enumerate(self.view_path):
            view = self.state_view_info.views[view_key]
            if view.view_class[-8:].lower() == "edittext":
                refer_name_path.append("edittext")
            else:
                refer_name_path.append(get_view_refer_name(view))
            if view_key in self.match_view2step.keys():
                can_finish_steps = self.match_view2step[view_key]
                for step_key, step_sim in can_finish_steps.items():
                    step_idx = int(step_key.split("_")[-1])
                    if self.is_step_finish[step_idx] == 0:
                        self.is_step_finish[step_idx] = max(self.is_step_finish) + 1
                        self.step_score.append(step_sim)
                        break
                    # else:
                    #     old_finish_arr = self.is_step_finish.copy()
                    #     new_finish_arr = self.is_step_finish.copy()
                    #     new_finish_arr[step_idx] = max(old_finish_arr) + 1
                    #     if self.get_finish_score(new_finish_arr) > self.get_finish_score(old_finish_arr):
                    #         print(old_finish_arr)
                    #         print(new_finish_arr)
                    #         self.is_step_finish[step_idx] = max(self.is_step_finish) + 1
                    #         self.step_score.append(step_sim)
                    #         break
            else:
                best_score = -1
                for step_key, step_view_sim in self.all_sim.items():
                    if view_key in step_view_sim.keys() and step_view_sim[view_key]["sim"] > best_score:
                        best_score = step_view_sim[view_key]["sim"]
                cur_step_sim = unmatch_scale * best_score
                self.step_score.append(cur_step_sim)
                refer_name_words = set(refer_name_path[path_idx].split())
                is_confirm_button = len(refer_name_words.intersection(confirm_button)) > 0
                if refer_name_path[path_idx - 1] == "edittext" and is_confirm_button:
                    self.create_score.append(create_reward)
        self.path_score = self.get_score()

    def get_score(self):
        step_punish_score = - step_punish * len(self.view_path)
        # print("step_punish_score", step_punish_score)
        step_match_score = sum(self.step_score)
        # print("step_match_score", step_match_score)
        step_finish_score = self.get_finish_score(self.is_step_finish)
        # print("step_finish_score", step_finish_score)
        return step_finish_score + step_punish_score + step_match_score

    def get_finish_score(self, finish_arr: list, disorder_scale=0.3):
        finish_score = 0
        # for step_idx, finish_idx in enumerate(self.is_step_finish):
        for step_idx, finish_idx in enumerate(finish_arr):
            if finish_idx == 0:
                continue
            order_scale = 1
            if step_idx != 0:
                # max_before = max(self.is_step_finish[:step_idx])
                # if finish_idx < max_before or max_before == 0:
                #     order_scale = disorder_scale
                for before_finish_idx in finish_arr[:step_idx]:
                    if finish_idx < before_finish_idx or before_finish_idx == 0:
                        if step_idx > finish_idx:
                            order_scale = order_scale * disorder_scale - 0.1 * (step_idx - finish_idx)
                        else:
                            order_scale = order_scale * disorder_scale
            finish_score += order_scale * finish_scale
        return finish_score

    def get_finish_count(self):
        return len(self.is_step_finish) - self.is_step_finish.count(0)

    def get_hash_key(self):
        state_path_str = "$".join(self.state_path)
        view_path_str = "$".join(self.view_path)
        path_str = state_path_str + "$$$" + view_path_str
        hash_key = hash(path_str)
        return hash_key

    def add_view(self, view_key):
        new_path = Path(self.graph_meta)

        new_view_path = self.view_path.copy()
        new_view_path.append(view_key)
        new_path.view_path = new_view_path

        src_state = self.state_path[-1]
        dst_state = self.all_transition[src_state][view_key]
        new_visited_state_times = self.visited_state_times.copy()
        dst_state_times = new_visited_state_times[dst_state] + 1
        new_visited_state_times[dst_state] += 1
        new_path.visited_state_times = new_visited_state_times

        new_state_path = self.state_path.copy()
        new_state_path.append(dst_state)
        new_path.state_path = new_state_path

        new_path.update_path()
        return dst_state_times, new_path

    def get_refer_name_str(self):
        refer_names = []
        for view_key in self.view_path:
            if 'KEY#' in view_key:
                refer_names.append(view_key)
            else:
                view_info = self.all_views[view_key]
                refer_names.append(get_view_refer_name(view_info))
        return "->".join(refer_names)


class StateNode():
    def __init__(self, state_id: str, visit_times: int, graph_meta):
        self.beam_size = 1000
        self.state_id = state_id
        self.visit_times = visit_times
        self.graph_meta = graph_meta
        self.all_state_nodes = self.graph_meta["all_state_nodes"]
        self.finish_info = self.graph_meta["finish_info"]
        self.all_path_info = self.graph_meta["all_path_info"]
        if state_id in self.graph_meta["all_transition"].keys():
            self.cur_transition = self.graph_meta["all_transition"][state_id]
        else:
            self.cur_transition = {}
        # if state_id in self.graph_meta["view_xpath_transition"].keys():
        #     self.cur_transition = self.graph_meta["view_xpath_transition"][state_id]
        # else:
        #     self.cur_transition = {}
        self.max_goal = self.graph_meta["max_goal"]
        self.max_revisit_times = self.graph_meta["max_revisit_times"]
        self.path_reach_state = {}
        self.finish_path = []

    def add_path(self, path: Path):
        path_hash_key = path.get_hash_key()
        if path_hash_key in self.path_reach_state.keys():
            return
        else:
            if path.state_path[-1] != self.state_id:
                print("#Error: not same, expect:", self.state_id, ", get:", path.state_path[-1])
                print(path.state_path)
                print(path.view_path)
                a = input("check!!!!")

            self.path_reach_state.setdefault(path_hash_key, {"expanded": False, "finished": False, "path": path,
                                                             "score": path.get_score()})

    def expand(self):
        if self.state_id == "state_4":
            print("now expand ", self.state_id, "#", self.visit_times)
            print(self.cur_transition)
        cur_path_score = [[path_key, path_info["score"]] for path_key, path_info in self.path_reach_state.items()]
        cur_path_score.sort(key=lambda x: -x[1])
        expand_path_key = [t[0] for t in cur_path_score[:self.beam_size]]
        expand_score = {}
        # for path_key, path_info in self.path_reach_state.items():
        for path_key in expand_path_key:
            path_info = self.path_reach_state[path_key]
            # 1. check path has expanded or finished?
            if path_info["expanded"] or path_info["finished"]:
                continue
            # 2. check path is finish
            cur_path = path_info["path"]
            path_finish_goal = cur_path.get_finish_count()
            # print("self.max_goal:", self.max_goal)
            # print("cur_path.get_finish_count:", cur_path.get_finish_count())
            if path_finish_goal == self.max_goal:
                path_info["finished"] = True
                path_info["expanded"] = True
                self.finish_info["finish_count"] += 1
                self.finish_info["finish_paths"].append([cur_path, cur_path.get_score()])

                state_path_str = "-".join(cur_path.state_path)
                # print("path " + state_path_str + " finished, score:", cur_path.get_score())
                continue
            # 3. expanded path
            path_info["expanded"] = True
            may_expand_path_record = {}
            for view_key, dst_state in self.cur_transition.items():
                if dst_state == "state_0":
                    continue
                if dst_state not in may_expand_path_record.keys():
                    may_expand_path_record.setdefault(dst_state, [])
                dst_state_times, new_path = cur_path.add_view(view_key)
                new_path_score = new_path.get_score()
                if dst_state_times <= self.max_revisit_times:
                    may_expand_path_record[dst_state].append([new_path, dst_state_times, new_path_score])
            for dst_state, may_expand_paths in may_expand_path_record.items():
                if len(may_expand_paths) == 0:
                    continue
                may_expand_paths.sort(key=lambda x: -x[2])
                if len(may_expand_paths) > 3:
                    may_expand_paths = may_expand_paths[:3]
                for path_info in may_expand_paths:
                    node_key = dst_state + "###" + str(path_info[1])
                    dst_state_node = self.all_state_nodes[node_key]
                    dst_state_node.add_path(path_info[0])
                    if node_key not in expand_score.keys():
                        expand_score.setdefault(node_key, path_info[2])
                    else:
                        if expand_score[node_key] < path_info[2]:
                            expand_score[node_key] = path_info[2]
                    self.all_path_info.append([path_info[0], path_info[2]])
                    if self.state_id == "state_4":
                        state_path_str = "-".join(cur_path.state_path)
                        print("path " + state_path_str + " expand, new_state:", node_key, "score:",
                                  path_info[0].get_score(), "finish:", path_info[0].is_step_finish)
                        print(path_info[0].get_refer_name_str())
        node_expand_list = [[node_key, score] for node_key, score in expand_score.items()]
        if self.state_id == "state_4":
            a = input(">>> continue?")
        return node_expand_list


if __name__ == '__main__':
    pass
