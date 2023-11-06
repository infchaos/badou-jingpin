新增三个模块，分别是查询填词、查询一个实体的所有属性和查询和实体具有某一关系的节点

1. %ENT%是谁填词的	Match (n)<-[:填词]-(m {NAME:"%ENT%"}) return n.NAME

2. %ENT%的详细信息	Match (n) where n.NAME="%ENT%" return properties(n)

3. 谁是%ENT%的%REL%	MATCH (n)-[:%REL%]->(m) WHERE n.NAME = "%ENT%" RETURN m.NAME

修改部分和新增部分在代码中有标出
