from UTG.states_and_views import StateViewInfo
from Recommend.util import get_view_refer_name

step_punish = 1
finish_dis_punish = 0.1
unmatch_scale = 1
finish_scale = 3
create_reward = 1.5
disorder_punish = 0.1


class PathRankingGraph():
    def __init__(self, match_meta: dict, state_view_info: StateViewInfo):
        self.max_revisit_times = 5
        self.state_view_info = state_view_info
        self.match_step2view = match_meta["match_step2view"]
        self.match_view2step = match_meta["match_view2step"]
        self.input_contents = match_meta["input_contents"]
        self.all_sim = match_meta["all_sim"]
        self.all_states = state_view_info.all_states
        self.states = state_view_info.states
        self.all_views = state_view_info.views
        self.view_xpath_transition = state_view_info.view_xpath_transition
        # print(self.view_xpath_transition)
        # print(state_view_info.view_str_transition)
        self.visited_view = set()
        self.all_transition = {state_id: {} for state_id in self.all_states}

        for view_key, view in self.all_views.items():
            if "state_" in view.dst_state and view.src_state != "state_0":
                self.all_transition[view.src_state].setdefault(view_key, view.dst_state)
            # if view.dst_state == "state_4" and view.src_state != "state_0":
            #     print("111 to state_4", view_key)
            # if view.dst_state == "state_3" and view.src_state != "state_0":
            #     print("111 to state_3", view_key)


        # for view_key in self.all_transition["state_6"]:
        #     view = state_view_info.views[view_key]
        #     print("#", self.all_transition["state_6"][view_key], get_view_refer_name(view))
        #     print(view_key)

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
                           "all_views": self.all_views, "all_path_info": self.all_path_info, "states": self.states,
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
            if expand_times >= 10000:
                break
            if self.finish_info["finish_count"] >= 100:
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
            for (finish_path, score) in self.finish_info["finish_paths"][:10]:
                state_path_str = "-".join(finish_path.state_path)
                print("path " + state_path_str + " finished, score:", finish_path.get_score())
                print(finish_path.get_refer_name_str())
                print(finish_path.is_step_finish)
                # break
            # here remove "max_goal": self.max_goal, I can't recall whexpay
            recommend_meta = {"recommend_paths": self.finish_info["finish_paths"],
                              "input_contents": self.input_contents, "max_goal": self.max_goal}
            # return self.finish_info["finish_paths"]
            return recommend_meta
        else:
            self.all_path_info.sort(key=lambda x: -x[1])
            len_thres = 3
            find_paths = []
            for find_path_info in self.all_path_info:
                find_path = find_path_info[0]
                if len(find_path.view_path) >= len_thres:
                    state_path_str = "-".join(find_path.state_path)
                    find_paths.append(find_path_info)
                    if len(find_paths) < 10:
                        print("find path " + state_path_str + ", score:", find_path.get_score(), ", create operation:", len(find_path.create_score))
                        print(find_path.get_refer_name_str())
                        click_views = [v.split(".")[-1] for v in find_path.view_path]
                        print(click_views)
                        print("-" * 20)
            # here remove "max_goal": self.max_goal, I can't recall why
            recommend_meta = {"recommend_paths": find_paths, "input_contents": self.input_contents, "max_goal": self.max_goal}
            # return self.all_path_info[:1]
            return recommend_meta


class Path():
    def __init__(self, graph_meta: dict):
        self.graph_meta = graph_meta
        self.all_states = graph_meta["all_states"]
        self.states = graph_meta["states"]
        self.all_transition = graph_meta["all_transition"]
        self.match_step2view = graph_meta["match_step2view"]
        self.match_view2step = graph_meta["match_view2step"]
        self.state_view_info = graph_meta["state_view_info"]
        self.all_sim = graph_meta["all_sim"]
        self.all_views = graph_meta["all_views"]
        self.max_goal = graph_meta["max_goal"]
        self.step_count = len(graph_meta["match_step2view"])
        self.is_step_finish = [0 for _ in range(len(self.match_step2view.keys()))]
        self.view_path = []
        self.state_path = []
        self.visited_state_times = {}
        self.step_score = []
        self.create_score = []
        self.path_score = 0
        self.finish_at = 114514
        self.finish_reward = []
        for state_id in self.all_states:
            self.visited_state_times.setdefault(state_id, 0)

    def update_path(self):
        confirm_button = ["save", "add", "create", "done", "ok", "confirm", "sign", "next", "unlock"]
        confirm_button = set(confirm_button)
        refer_name_path = []
        step_can_match = [int(k.split("_")[-1]) for k, v in self.match_step2view.items() if v["match_count"] > 0]
        if len(step_can_match) == 0:
            next_step_match = {}
        else:
            next_step_match = {step_can_match[i]: step_can_match[i + 1] for i in range(len(step_can_match) - 1)}
            next_step_match.setdefault(step_can_match[-1], step_can_match[-1])
        for path_idx, view_key in enumerate(self.view_path):
            view = self.state_view_info.views[view_key]
            if view.view_class[-8:].lower() == "edittext":
                refer_name_path.append("edittext")
            else:
                refer_name_path.append(get_view_refer_name(view))
            if view_key in self.match_view2step.keys():
                if "ROTATE" in view_key and path_idx != len(self.view_path) - 1:
                    self.step_score.append(-999)
                    continue
                if "RESTART" in view_key and path_idx != len(self.view_path) - 1:
                    self.step_score.append(-999)
                    continue
                can_finish_steps = self.match_view2step[view_key]
                first_try = False
                for step_key, step_sim in can_finish_steps.items():
                    step_idx = int(step_key.split("_")[-1])
                    if max(self.is_step_finish) == 0:
                        last_finish_step = min(step_can_match) if len(step_can_match) > 0 else 0
                    else:
                        last_finish_step = 0
                        for i, finish_idx in enumerate(self.is_step_finish):
                            if finish_idx > 0:
                                last_finish_step = next_step_match[i]
                    if self.is_step_finish[step_idx] == 0 and step_idx - last_finish_step < 2:
                        self.is_step_finish[step_idx] = max(self.is_step_finish) + 1
                        if "_FillInfo" in view_key:
                            self.step_score.append(step_sim + 0.0001)
                        else:
                            self.step_score.append(step_sim)
                        if "###KEY#BACK" in view_key:
                            cur_finish_reward = min(1, 1 - (step_idx - last_finish_step))
                        else:
                            cur_finish_reward = min(1, 1 - finish_dis_punish * (step_idx - last_finish_step))
                        self.finish_reward.append(cur_finish_reward)
                        first_try = True
                        break
                    # elif max(self.is_step_finish) == step_idx + 1:
                    #     self.is_step_finish[step_idx] = max(self.is_step_finish) + 1
                    #     self.step_score.append(step_sim)
                    #     break
                if not first_try:
                    views_before = self.view_path[:path_idx]
                    cur_step_sim = list(can_finish_steps.values())[0]
                    if view.view_class[-8:].lower() == "edittext":
                        self.step_score.append(0)
                    elif views_before.count(view_key) <= 2:
                        # if self.view_path[path_idx - 1] == self.view_path[path_idx]:
                        #     self.step_score.append(-10)
                        # else:
                        self.step_score.append(unmatch_scale * cur_step_sim)
                    else:
                        self.step_score.append(0.5 * unmatch_scale * cur_step_sim)
                is_path_finish = len(self.is_step_finish) - self.is_step_finish.count(0) == self.max_goal
                if is_path_finish and self.finish_at == 114514:
                    self.finish_at = path_idx + 1
            else:
                best_score = -1
                for step_key, step_view_sim in self.all_sim.items():
                    if view_key in step_view_sim.keys() and step_view_sim[view_key]["sim"] > best_score:
                        best_score = step_view_sim[view_key]["sim"]
                cur_step_sim = unmatch_scale * best_score
                refer_name_words = set(refer_name_path[path_idx].split())
                is_confirm_button = len(refer_name_words.intersection(confirm_button)) > 0
                cur_state = view_key.split("###")[0]
                cur_activity = self.states[cur_state].activity
                if view.view_class[-8:].lower() == "edittext":
                    if self.view_path[path_idx - 1] == self.view_path[path_idx]:
                        new_step_sim = -0.1
                        self.step_score.append(new_step_sim)
                    else:
                        new_step_sim = max(cur_step_sim, 0.1)
                        self.step_score.append(new_step_sim)
                elif "IntroActivity" in cur_activity and ("next" in refer_name_words or "done" in refer_name_words):
                    self.step_score.append(step_punish - 0.1)
                elif "_Scroll" in view_key:
                    self.step_score.append(cur_step_sim - 0.01)
                else:
                    self.step_score.append(cur_step_sim)
                # if view.src_state == "state_6" and view.dst_state == "state_6":
                #     print("### step sim:", get_view_refer_name(view), cur_step_sim)

                # if refer_name_path[path_idx - 1] == "edittext" and is_confirm_button:
                if "_FillInfo" in view_key:
                    # print("### get create reward")
                    if self.step_count == 1:
                        max_fill_retry = 2
                    else:
                        max_fill_retry = 1
                    if self.create_score.count(view_key) < max_fill_retry:
                        self.create_score.append(view_key)
        self.path_score = self.get_score()

    def get_score(self, debug=False):
        step_punish_score = - step_punish * len(self.view_path)
        if debug:
            print("step_punish_score", step_punish_score)
        step_match_score = sum(self.step_score)
        if debug:
            print("step_match_score", step_match_score)

        # old finish score
        if self.get_finish_score(self.is_step_finish) > 0:
            step_finish_score = self.get_finish_score(self.is_step_finish) + len(self.create_score) * create_reward
        else:
            if self.step_count == 1:
                max_create_count = 2
            else:
                max_create_count = 1
            step_finish_score = 1.5 * min(len(self.create_score), max_create_count) * create_reward
        if debug:
            print("step_finish_score", step_finish_score)
        return step_finish_score + step_punish_score + step_match_score

    def get_finish_score(self, finish_arr: list):
        finish_score = 0
        # for step_idx, finish_idx in enumerate(self.is_step_finish):
        for step_idx, finish_idx in enumerate(finish_arr):
            if finish_idx == 0:
                continue
            disorder_count = 0
            for before_finish_idx in finish_arr[:step_idx]:
                if before_finish_idx == 0 or before_finish_idx > finish_idx:
                    disorder_count += 1
            for after_finish_idx in finish_arr[step_idx + 1:]:
                if after_finish_idx < finish_idx and after_finish_idx != 0:
                    disorder_count += 1
            finish_score += max(0.2, 1 - disorder_count * disorder_punish)
        return finish_score * finish_scale

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
        self.beam_size = 50
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
        # if self.state_id == "state_1":
        #     print("now expand ", self.state_id, "#", self.visit_times)
        #     print(self.cur_transition)
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
            # 2. check path is finish, let the finish path can walk 2 step more
            cur_path = path_info["path"]
            path_finish_goal = cur_path.get_finish_count()
            path_view_len = len(cur_path.view_path)
            # if path_finish_goal == self.max_goal:
            #     # stop expand at finish all goal
            #     path_info["finished"] = True
            #     path_info["expanded"] = True
            #     self.finish_info["finish_count"] += 1
            #     self.finish_info["finish_paths"].append([cur_path, cur_path.get_score()])
            #
            #     state_path_str = "-".join(cur_path.state_path)
            #     continue
            if path_finish_goal == self.max_goal and self.max_goal > 0:
                path_info["finished"] = True
                path_info["expanded"] = True
                self.finish_info["finish_count"] += 1
                self.finish_info["finish_paths"].append([cur_path, cur_path.get_score()])
                if path_view_len > cur_path.finish_at + 2:
                    # only expand 2 step after finish
                    continue

            # 3. expanded path
            path_info["expanded"] = True
            may_expand_path_record = {}
            for view_key, dst_state in self.cur_transition.items():
                # if self.state_id == "state_6":
                #     print(self.state_id, view_key)
                # if dst_state == "state_0":
                #     continue
                if dst_state not in may_expand_path_record.keys():
                    may_expand_path_record.setdefault(dst_state, [])
                dst_state_times, new_path = cur_path.add_view(view_key)
                new_path_score = new_path.get_score()
                if dst_state_times <= self.max_revisit_times:
                    may_expand_path_record[dst_state].append([new_path, dst_state_times, new_path_score])
                    # if self.state_id == "state_8" and self.visit_times <= 2:
                    #     state_path_str = "-".join(new_path.state_path)
                    #     print("path " + state_path_str + " expand, score:",
                    #           new_path.get_score(debug=True), "finish:", new_path.is_step_finish)
                    #     print(new_path.get_refer_name_str())
                    # if self.state_id == "state_10":
                    #     state_path_str = "-".join(new_path.state_path)
                    #     print("path " + state_path_str + " expand, score:",
                    #           new_path.get_score(debug=True), "finish:", new_path.is_step_finish)
                    #     print(new_path.get_refer_name_str())
            for dst_state, may_expand_paths in may_expand_path_record.items():
                if len(may_expand_paths) == 0:
                    continue
                may_expand_paths.sort(key=lambda x: -x[2])
                if len(may_expand_paths) > 1:
                    may_expand_paths = may_expand_paths[:1]
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
                    # if self.state_id == "state_6":
                    #     state_path_str = "-".join(cur_path.state_path)
                    #     print("path " + state_path_str + " expand, new_state:", node_key, "score:",
                    #               path_info[0].get_score(), "finish:", path_info[0].is_step_finish)
                    #     print(path_info[0].get_refer_name_str())
        node_expand_list = [[node_key, score] for node_key, score in expand_score.items()]
        # if self.state_id == "state_6":
        #     # a = input(">>> continue?")
        #     print("#" * 20)
        return node_expand_list


if __name__ == '__main__':
    # step_can_match = [0, 2, 3, 4, 6]
    # next_step_match = {step_can_match[i]: step_can_match[i + 1] for i in range(len(step_can_match) - 1)}
    # next_step_match.setdefault(step_can_match[-1], step_can_match[-1])
    # print(next_step_match)
    # step_can_match = [2]
    # next_step_match = {step_can_match[i]: step_can_match[i + 1] for i in range(len(step_can_match) - 1)}
    # next_step_match.setdefault(step_can_match[-1], step_can_match[-1])
    # print(next_step_match)
    finish_arr = [1, 2, 0, 0, 0]
    finish_score = 0
    for step_idx, finish_idx in enumerate(finish_arr):
        if finish_idx == 0:
            continue
        disorder_count = 0
        for before_finish_idx in finish_arr[:step_idx]:
            if before_finish_idx == 0 or before_finish_idx > finish_idx:
                disorder_count += 1
        for after_finish_idx in finish_arr[step_idx + 1:]:
            if after_finish_idx < finish_idx and after_finish_idx != 0:
                disorder_count += 1
        finish_score += max(0.2, 1 - disorder_count * disorder_punish)
    print(finish_score)

