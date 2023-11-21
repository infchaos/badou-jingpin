import json
import pandas
import re

'''
对话系统
基于场景脚本完成多轮对话
作业：添加重听功能，主要改动在get_intent()与.json文件（添加重听节点以及其他节点的childnode）。
'''

class DialogSystem:
    def __init__(self):
        self.load()

    def load(self):
        self.all_node_info = {}   # key = 节点id， value = node info
        self.load_scenrio("scenario-买衣服.json")  # 加载场景脚本信息
        self.load_scenrio("scenario-看电影.json")  # 加载场景脚本信息
        self.slot_info = {}  # key = slot, value = [反问，可能取值]
        self.load_templet()  # 加载槽位信息，存放到slot_info中
    
    def init_memory(self):
        memory = {}
        memory["available_node"] = ["scenario-买衣服-node1", "scenario-看电影-node1"]
        return memory
    
    def load_scenrio(self, path): 
        scenario_name = path.replace(".json", "")  # 去掉.json
        with open(path, "r", encoding="utf-8") as f:
            scenario_data = json.load(f)  # 加载json文件
        for node_info in scenario_data:  # 遍历每个节点的信息
            node_id = node_info["id"]
            node_id = scenario_name + "-" + node_id  # 为了应对多个场景脚本节点名重复的问题，将节点名加上场景名
            if "childnode" in node_info:  # 如果当前节点有子节点，即不是末节点：
                node_info["childnode"] = [scenario_name + "-" + child for child in node_info["childnode"]]  # 给每个子节点都加上场景名
            self.all_node_info[node_id] = node_info  # 所有场景脚本的所有节点信息都存放在all_node_info中
    
    def load_templet(self):
        df = pandas.read_excel("./slot_fitting_templet.xlsx")  # 读取.xlsx文件
        for i in range(len(df)):  # 遍历df文件的每一行：
            slot = df["slot"][i]  # 读取槽位信息，例如：#服装类型#
            query = df["query"][i]  # 反问
            values = df["values"][i]   # 这个槽位可能的取值
            self.slot_info[slot] = [query, values]  # 反问和可能取值存储在同一个列表中

    def run(self, query, memory):
        if memory == {}:
            memory = self.init_memory()  # 初始化
        memory["query"] = query  # query是用户的输入
        memory = self.nlu(memory)  # 语义理解：意图识别、获取槽位信息。
        memory = self.dst(memory)  # 对话状态跟踪：判断槽位信息是否填充完毕。
        memory = self.pm(memory)  # 选择不同策略：反问 or 回复。
        memory = self.nlg(memory)  # 将槽位信息替换到回复模板中，生成回复信息。
        return memory
    
    def nlu(self, memory):
        # 语义解析
        memory = self.get_intent(memory)  # 意图识别：命中最匹配的节点
        memory = self.get_slot(memory)  # 获取槽位信息
        return memory
    
    def get_intent(self, memory):
        # 获取意图
        last_hit_node = memory.get("hit_node", [])  #获取上一次命中的节点
        hit_node = None
        hit_score = -1
        for node_id in memory["available_node"]:  # 可选的节点：最开始的时候是每个场景的node1
            score = self.get_node_score(node_id, memory)  # 得到当前节点的匹配度
            if score > hit_score:  # 找到最匹配的节点，并记录匹配得分
                hit_node = node_id
                hit_score = score
        if "node5" in hit_node:  # 设置node5为重听节点，如果命中该节点，将memory中的命中节点赋值为上一步命中的节点。
            memory["hit_node"] = last_hit_node
        else:  # 如果命中的不是重听节点，则正常更新命中节点
            memory["hit_node"] = hit_node
            memory["hit_score"] = hit_score
        return memory
    
    def get_node_score(self, node_id, memory):
        # 计算意图得分
        intent_list = self.all_node_info[node_id]["intent"]  # 取出当前节点的内容，可能会有多个（同一意图，不同说法）
        query = memory["query"]  # 取出用户的意图
        scores = []
        for intent in intent_list:
            score = self.similarity(query, intent)  # 计算用户的意图与当前节点的相似度
            scores.append(score) 
        return max(scores)  # 返回一个最大值即可
    
    def similarity(self, query, intent):
        # 文本相似度计算，使用jaccard距离
        intersect = len(set(query) & set(intent))
        union = len(set(query) | set(intent))
        return intersect / union

    def get_slot(self, memory):
        # 获取槽位
        hit_node = memory["hit_node"]  # 得到上一步意图识别选中的节点
        for slot in self.all_node_info[hit_node].get("slot", []):  # 获取选中节点的槽位信息，如果没有则返回空列表
            if slot not in memory:  # 如果当前槽位信息在memory中不存在，说明该槽位没有填充
                values = self.slot_info[slot][1]  # 取出该槽位可能的取值
                info = re.search(values, memory["query"])  # 用正则表达式从用户输入的意图中查找可能的取值
                if info is not None:  # 如果找到了
                    memory[slot] = info.group()  # 填充当前槽位
        return memory

    def dst(self, memory):
        # 对话状态跟踪
        hit_node = memory["hit_node"]  # 获取当前命中节点
        for slot in self.all_node_info[hit_node].get("slot", []):  # 遍历当前节点的所有槽位
            if slot not in memory:  # 如果有槽位没填充
                memory["require_slot"] = slot  # 记录下来
                return memory  # 直接跳出dst()
        memory["require_slot"] = None  # 如果都填充了，记录为None
        return memory

    def pm(self, memory):
        # 对话策略执行
        if memory["require_slot"] is not None:  # 如果有槽位信息没填充，则执行反问策略
            # 反问策略
            memory["available_node"] = [memory["hit_node"]]  # 将可用节点更新为当前命中的节点，因为还要继续在当前节点停留
            memory["policy"] = "ask"  # 选择反问策略
        else:
            # 回答
            # self.system_action(memory) #系统动作完成下单，查找等
            memory["available_node"] = self.all_node_info[memory["hit_node"]].get("childnode", [])  # 如果槽位都填充了，则获取当前节点的子节点列表
            memory["policy"] = "answer"  # 选择回复策略
        return memory

    def nlg(self, memory):
        # 自然语言生成  
        if memory["policy"] == "ask":  # 如果要反问：
            slot = memory["require_slot"]  # 先获取没有填充的槽位信息
            reply = self.slot_info[slot][0]   # 找到.xlsx文件中的反问文本：[query，values]中的query
        else:  # 如果要回复：
            if self.all_node_info[memory["hit_node"]]["response"] == "重复":
                return memory
            reply = self.all_node_info[memory["hit_node"]]["response"]  # 找到.xlsx文件中应对当前节点的回复文本
            reply = self.replace_templet(reply, memory)  # 将回复文本中的一些槽位替换为当前信息。
        memory["reply"] = reply
        return memory

    def replace_templet(self, reply, memory):
        # 替换模板中的槽位
        hit_node = memory["hit_node"]
        for slot in self.all_node_info[hit_node].get("slot", []):  # 获取所有填充的槽位信息
            reply = re.sub(slot, memory[slot], reply)  # 用正则表达式将槽位信息替换到回复文本中
        return reply


if __name__ == '__main__':
    ds = DialogSystem()
    # print(ds.all_node_info)
    # print(ds.slot_info)
    memory = {}
    while True:
        query = input("用户输入：")
        memory = ds.run(query, memory)
        print(memory)
        print(memory["reply"])
