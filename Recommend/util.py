import difflib
import re
import Levenshtein
from UTG.view import View
import json
import matplotlib.pyplot as plt
from nltk.corpus import stopwords
from nltk.stem import SnowballStemmer
from nltk.corpus import wordnet as WN


def get_str_cover(clean_query, clean_candi):
    # clean_query = clean_non_ascii(str_query)
    query_words = clean_query.split(" ")
    # clean_candi = clean_non_ascii(str_candi)
    candi_words = clean_candi.split(" ")
    cover_len = 0
    low = len(clean_candi)
    high = 0
    for word in query_words:
        match_res = difflib.get_close_matches(word, candi_words, cutoff=0.8)
        if len(match_res) != 0:
            cover_len += len(word)
            cur_low = clean_candi.index(match_res[0])
            cur_high = clean_candi.index(match_res[0]) + len(match_res[0])
            if cur_low < low:
                low = cur_low
            if cur_high > high:
                high = cur_high
    if low == len(clean_candi):
        low = 0
    if high == 0:
        high = len(clean_candi)
    edit_dis = Levenshtein.distance(clean_query, clean_candi[low:high])
    return cover_len, edit_dis, high - low


# def clean_non_ascii(text):
#     text = re.sub(r'[^\x00-\x7f]', " ", text)
#     text = re.sub(r'\s+', " ", text)
#     return text


def get_str_sim(str_query, str_candi):
    if len(str_candi) > 100 or len(str_candi) == 0:
        return -1, 0, 0
    clean_query = clean_non_ascii(str_query)
    clean_candi = clean_non_ascii(str_candi)
    cover_len, edit_dis, match_len = get_str_cover(clean_query, clean_candi)

    cover_radio = cover_len / len(clean_query.replace(" ", ""))
    edit_radio = edit_dis / max(len(clean_query), match_len)
    exceed_punish = (len(clean_candi) - match_len) / (len(clean_candi) + 1e-6)
    return cover_radio, edit_radio, exceed_punish


def get_view_refer_name(view_info: View):
    # Priority 1: for EditText, return its resource id for name, or neighbor text
    if view_info.view_class[-8:].lower() == "edittext":
        return get_edittext_name(view_info)

    # Priority 2: for checkbox, radiobutton, switch, return its neighbor text for name
    if view_info.view_class[-8:].lower() == "checkbox" or view_info.view_class[-11:].lower() == "radiobutton" \
            or view_info.view_class[-6:].lower() == "switch":
        return get_checktext_name(view_info)

    # Priority 3: case layout, text from child
    if view_info.view_class[-6:].lower() == "layout" or "linearlayout" in view_info.view_class.lower() \
            or view_info.view_class[-7:].lower() == "spinner" or view_info.view_class[-9:].lower() == "viewgroup":
        return get_layout_name(view_info)
    return get_general_name(view_info)


def get_edittext_name(view_info: View):
    # EditText 1: for EditText, return its resource id for name, or neighbor text
    if view_info.resource_id != "none" and len(view_info.resource_id.split()) > 1:
        clean_id = clean_resource_id(view_info.resource_id)
        keywords = ["email", "name", "pass"]
        has_keyword = False
        for keyword in keywords:
            if keyword in clean_id:
                has_keyword = True
                break
        has_sibling_text = len(view_info.sibling_text) > 0 and view_info.sibling_text[0] != "none"
        use_flag1 = (len(clean_id.split()) >= 2 and len(clean_id.split()) <= 3)
        use_flag2 = (not has_sibling_text) and (len(clean_id.split()) == 1 or len(clean_id.split()) >= 4)
        if use_flag1 or use_flag2 or has_keyword:
            return clean_id

    # EditText 2: return not none sibling text
    if len(view_info.sibling_text) > 0:
        for sibling_text in view_info.sibling_text:
            clean_sibling_text = clean_non_ascii(sibling_text, 8)
            if clean_sibling_text != "none" and len(clean_sibling_text) > 0:
                return clean_sibling_text

    # EditText 3: return not none parent text
    if view_info.parent_text != "none":
        clean_parent_text = clean_non_ascii(view_info.parent_text, 8)
        if clean_parent_text != "none" and len(clean_parent_text) > 0:
            return clean_parent_text

    # EditText 3: no idea what to return, return neighbor text
    return clean_non_ascii(view_info.neighbor_text, 8)


def get_checktext_name(view_info: View):
    # checktext 1: for checkbox, radiobutton, switch, return its neighbor text for name
    if len(view_info.sibling_text) > 0:
        for sibling_text in view_info.sibling_text:
            clean_sibling_text = clean_non_ascii(sibling_text, 8)
            if clean_sibling_text != "none" and len(clean_sibling_text) > 0:
                return clean_sibling_text

    # checktext 2: no idea what to return, return neighbor text
    return clean_non_ascii(view_info.neighbor_text, 8)


def get_layout_name(view_info: View):
    # layout 1: case layout, text from child
    if len(view_info.child_text) > 0:
        for child_text in view_info.child_text:
            clean_child_text = clean_non_ascii(child_text[0], 8)
            if clean_child_text != "none" and len(clean_child_text) > 0:
                return clean_child_text

    # layout 2: case layout, text from child
    if view_info.resource_id != "none":
        clean_id = clean_resource_id(view_info.resource_id)
        if len(clean_id.split(" ")) >= 2 and len(clean_id.split(" ")) <= 4:
            # return view_info["resource_id"].lower()
            return clean_id

    # layout 2: no idea what to return, return neighbor text
    return clean_non_ascii(view_info.neighbor_text, 8)


def get_general_name(view_info: View):
    # if view_info.src_state == "state_1" and "imagebutton" in view_info.view_type.lower():
    #     print(view_info.resource_id)
    #     print(view_info.content_desc)
    # Priority 1: text from self
    if view_info.text != "none":
        return clean_non_ascii(view_info.text, 8)
    if view_info.content_desc != "none":
        return clean_non_ascii(view_info.content_desc, 8)
    if view_info.hint != "none":
        return clean_non_ascii(view_info.hint, 8)

    # Priority 2: view's resource id longer than 2 words, it may be a meaningful identifier
    if view_info.resource_id != "none" and len(view_info.resource_id.split()) >= 1:
        clean_id = clean_resource_id(view_info.resource_id)
        if len(clean_id.split()) >= 1:
            return clean_id

    # Priority 3: return not none sibling text
    if len(view_info.sibling_text) > 0:
        for sibling_text in view_info.sibling_text:
            clean_sibling_text = clean_non_ascii(sibling_text, 8)
            if clean_sibling_text != "none" and len(clean_sibling_text) > 0:
                return clean_sibling_text

    # Priority 4: return only one child_text
    if len(view_info.child_text) > 0:
        for child_text in view_info.child_text:
            clean_child_text = clean_non_ascii(child_text[0], 8)
            if clean_child_text != "none" and len(clean_child_text) > 0:
                return clean_child_text

    # Priority 5: no idea what to return, return neighbor text
    return clean_non_ascii(view_info.neighbor_text, 8)


def clean_resource_id(resource_id: str):
    resource_id = re.sub(r'([a-z])([A-Z])', r'\1 \2', resource_id).lower()
    resource_id = re.sub("[^a-z]", " ", resource_id).strip()
    useless_words = ["edittext", "button", "none", "view", "textview", "action", "fab"]
    words = resource_id.strip().split(" ")
    use_word = []
    for word in words:
        word_char = set(word)
        # drop word that maybe abbreviation from edittext/button, like: edit, edt, ed, text...
        use_flag = True
        for useless_word in useless_words:
            inter_with_useless_word = word_char.intersection(set(useless_word))
            if len(word_char) <= len(inter_with_useless_word):
                use_flag = False
                break
        if use_flag:
            use_word.append(word)
    if len(use_word) == 0:
        return "none"
    else:
        return " ".join(use_word)


def clean_non_ascii(ori_str, max_len=5):
    clean_str = re.sub("[^\x00-\x7f]", " ", ori_str.lower())
    clean_str = re.sub("\s+", " ", clean_str).strip()
    if len(clean_str.split()) > max_len:
        clean_str_tokens = clean_str.split()[:max_len]
        clean_str = " ".join(clean_str_tokens)
    if len(clean_str.strip()) == 0:
        return "none"
    return clean_str


class SimpleWordAnalyser():
    def __init__(self):
        self.stop_words = stopwords.words('english')
        self.all_stop_words = self.stop_words.copy()
        self.all_stop_words.extend(["button", "long", "like", "long", "invalid", "one", "option", "just", "phone"])
        self.snowball_stemmer = SnowballStemmer("english")

        self.verbs = ['select', 'choose', 'swipe', 'press', 'type', 'enter', 'change', 'switch', 'enable', 'open',
                      'clicking', 'disable', 'launch', 'set', 'tap', 'click', 'go', 'turn', 'write', 'input', 'put',
                      "crash", "trying", "create", "check", "initiate"]
        self.stem_verbs = [self.snowball_stemmer.stem(w) for w in self.verbs]
        self.relevant_word = ["settings", "setting", "about"]

    def clean_irrelevant_word(self, step_str: str):
        relevant_words = []
        relevant_words_split = []
        not_in_dict_words = []
        maybe_input_contents = []
        quote_words = []
        special_input_map = {"apostrophe": "helloworld'", "space": " ", "quote": '"', "quotation": '"'}
        stem_special_input_map = {self.snowball_stemmer.stem(k): v for k, v in special_input_map.items()}
        quote_items1 = re.findall(r'\".*?\"', step_str)
        quote_items2 = re.findall(r"\'.*?\'", step_str)
        quote_items = quote_items1 + quote_items2
        for quote_item in quote_items:
            # if " " in quote_item:
            #     continue
            quote_item = quote_item[1:-1]
            if " " not in quote_item:
                in_dict_res = self.check_is_in_dict(quote_item)
                if in_dict_res[0] != 0:
                    maybe_input_contents.append(quote_item)
            else:
                for quote_word in quote_item.split(" "):
                    in_dict_res = self.check_is_in_dict(quote_word)
                    if in_dict_res[0] == 0:
                        quote_words.append(quote_word)
        if "\t" in step_str:
            step_str = step_str.split("\t")[1]
        step_str = step_str.replace("e.g.", " ").lower()
        step_str = re.sub("[^a-z]", " ", step_str)
        step_str = re.sub(r"\s+", " ", step_str)
        for word in step_str.split():
            in_dict_res = self.check_is_in_dict(word)
            if in_dict_res[0] == 1 or in_dict_res[0] == 2:
                not_in_dict_words.append(word)
            stem_word = self.snowball_stemmer.stem(word)
            if word in self.relevant_word:
                if in_dict_res[0] == 1:
                    relevant_words.append(word)
                    relevant_words_split.extend(in_dict_res[1])
                else:
                    relevant_words.append(word)
                    relevant_words_split.append(word)
            if (stem_word not in self.stem_verbs and stem_word not in self.all_stop_words) or word in quote_words:
                if in_dict_res[0] != 2:
                    if in_dict_res[0] == 1:
                        relevant_words.append(word)
                        relevant_words_split.extend(in_dict_res[1])
                    else:
                        relevant_words.append(word)
                        relevant_words_split.append(word)
            if stem_word in stem_special_input_map.keys():
                maybe_input_contents.append(stem_special_input_map[stem_word])
        analyse_res = {"relevant_words": relevant_words, "relevant_words_split": relevant_words_split,
                       "not_in_dict_words": not_in_dict_words, "maybe_input_contents": maybe_input_contents}
        return analyse_res

    def check_is_in_dict(self, word: str):
        if word.lower() == "sync":
            return [1, ["synchronization"]]
        if not WN.synsets(word) and word not in self.stop_words:
            # print("not in dict:", word)
            for i in range(1, len(word)):
                sub_word1 = word[:i]
                sub_word1_in_dict = WN.synsets(sub_word1) or sub_word1 in self.stop_words
                sub_word2 = word[i:]
                sub_word2_in_dict = WN.synsets(sub_word2) or sub_word2 in self.stop_words
                if sub_word1_in_dict and sub_word2_in_dict:
                    # print("joint word:", word, ":", sub_word1, sub_word2)
                    return [1, [sub_word1, sub_word2]]
            return [2, [word]]
        else:
            return [0, [word]]

    def get_stem_res(self, view_refer_name: str):
        view_refer_name = re.sub("[^a-z]", " ", view_refer_name.lower())
        view_refer_name = re.sub(r"\s+", " ", view_refer_name)
        stem_res = set()
        for view_word in view_refer_name.split():
            stem_res.add(self.snowball_stemmer.stem(view_word))
        return stem_res


if __name__ == '__main__':
    a = SimpleWordAnalyser()
    # print(a.clean_irrelevant_word('click on the "add to" option'))
    print(a.check_is_in_dict("synchronization"))