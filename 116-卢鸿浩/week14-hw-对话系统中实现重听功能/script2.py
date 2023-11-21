import json
import re
import pandas

def get_similarity_score(query, intent):
    #计算文本相似度
    interset = set(query)&set(intent)
    union = set(query)|set(intent)
    return len(interset)/len(union)

def get_intent_score(query, intent):
    score = get_similarity_score(query, intent)
    return score

class DialogSystem:
    # 对话系统
    def __init__(self):
        self.load()

    def load(self):
        # 加载数据
        self.all_node_info = {}
        self.slot_info = {}
        self.load_scenario("scenario-买衣服.json")
        self.load_templet("./slot_fitting_templet.xlsx")

    def load_scenario(self, file_name):
        scenario_name = file_name.replace(".json","")
        scenario_data = {}
        print(type(scenario_data))
        with open(file_name, "r", encoding = "utf-8") as f:
            scenario_data = json.load(f)
        for node_info in scenario_data:
            node_id = node_info["id"]
            node_id_new = scenario_name + '-' + node_id
            if "childnode" in node_info:
                node_info["childnode"]  = [scenario_name + '-' + child for child in node_info["childnode"]]
            self.all_node_info[node_id_new] = node_info

    def load_templet(self, file_name):
        slot_data = pandas.read_excel(file_name)
        for i in range(len(slot_data)):
            slot = slot_data["slot"][i]
            query = slot_data["query"][i]
            values = slot_data["values"][i]
            self.slot_info[slot] = {"query": query, "values": values}

    def run(self, query, memory):
        if(memory == {}):
            memory["available_node_list"] = ['scenario-买衣服-node1']
        memory["query"] = query
        #对话系统主要流程
        memory = self.nlu(memory)
        memory = self.dst(memory)
        memory = self.dm(memory)
        memory = self.nlg(memory)
        return memory

    def nlu(self, memory):
        #自然语言理解
        memory = self.get_intent(memory)
        memory = self.get_slot(memory)
        return memory

    def get_intent(self, memory):
        #获取意图
        query = memory["query"]
        hit_score = -1
        hit_node = None
        for node_id in memory["available_node_list"]:
            print(self.all_node_info[node_id])
            score = self.get_intent_list_score(query, self.all_node_info[node_id]["intent"])
            print(query, " ", score)
            if(score > hit_score):
                hit_score = score
                hit_node = node_id

        memory["hit_node"] = hit_node
        memory["hit_score"] = hit_score
        print(hit_node)
        return memory

    def get_intent_list_score(self, query, intent_list):
        #获取query和intent list中所有intent的最大值
        scores = []
        for intent in intent_list:
            scores.append(get_intent_score(query, intent))
        return max(scores)

    def get_slot(self, memory):
        #获取槽位信息
        query = memory["query"]
        hit_node = memory["hit_node"]
        print(hit_node)
        for slot in self.all_node_info[hit_node].get("slot", []): # 如果存在槽位，则遍历所有槽位
            if slot not in memory:
                slot_values = self.slot_info[slot]["values"]   # 获取所有slot可能的值
                info = re.search(slot_values, query)           # 从query中查询是否存在以上值
                if info is not None:
                    memory[slot] = info.group()
        return memory

    def dst(self, memory):
        #对话状态跟踪
        # 这一步是判读该节点所需槽位是否全部都已经获得
        hit_node = memory["hit_node"]
        for slot in self.all_node_info[hit_node].get("slot", []):
            if slot not in memory:
                memory["require_slot"] = slot
                return memory
        memory["require_slot"] = None
        return memory

    def dm(self, memory):
        #对话策略管理
        # 这一步，用来判断继续获取槽位信息（反问）还是回答（结束提问）,并更新available_node_list
        require_slot = memory["require_slot"]
        if require_slot is not None:
            # 反问，获取槽位信息
            memory["policy"] = "ask"
            memory["available_node_list"] = [memory["hit_node"]]
        else:
            # 回答
            memory["policy"] = "answer"
            memory["available_node_list"] = self.all_node_info[memory["hit_node"]].get("childnode", [])
        return memory


    def nlg(self, memory):
        #自然语言生成
        if memory["policy"] == "ask":
            slot = memory["require_slot"]
            slot_query = self.slot_info[slot]["query"]
            memory["reply"] = slot_query + "?"
        elif memory["policy"] == "answer":
            if("hit_node"!="scenario-买衣服-node5"):
                reponse = self.all_node_info[memory["hit_node"]]["response"]
                memory["reply"] = self.replace_templet(reponse, memory)
        return memory

    def replace_templet(self, reponse, memory):
        # 在reponse中，替换到实际槽位信息
        hit_node = memory["hit_node"]
        for slot in self.all_node_info[hit_node].get("slot", []):  #遍历当前节点的所有槽位
            reponse = re.sub(slot, memory[slot], reponse)
        return reponse


if __name__ == '__main__':
    ds = DialogSystem()

    memory = {}

    print(ds.all_node_info)
    print("++++")
    print(ds.slot_info)

    while 1:
        query = input('用户请输入:')
        memory = ds.run(query, memory)
        print(memory["reply"])
        print(memory["hit_node"])
