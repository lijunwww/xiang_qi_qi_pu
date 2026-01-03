from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class VariationNode:
    """变着节点：包含本条变着的走法和其内部的多层子变着。
    - `san_moves`: 本变着的走法序列（中文记谱SAN列表）
    - `children`: { pivot_index(int, 1-based within this node) : List[VariationNode] }
    """
    var_id: int
    name: str
    san_moves: List[str]
    san_comments: List[str] = field(default_factory=list)
    children: Dict[int, List['VariationNode']] = field(default_factory=dict)

@dataclass
class VariationManager:
    """
    支持多层变着的管理器。
    - 顶层结构为 { pivot_ply(int) : List[VariationNode] }
    - 每个 VariationNode 可在其内部任意位置挂子变着（通过 children 字段），形成树结构
    - 提供序列化/反序列化以支持 JSON 保存/读取
    """
    variations: Dict[int, List[VariationNode]] = field(default_factory=dict)
    _next_var_id: int = 1
    _id_map: Dict[int, VariationNode] = field(default_factory=dict)

    def _register(self, node: VariationNode, parent_id: Optional[int] = None):
        self._id_map[node.var_id] = node

    def _find_parent_path(self, target_id: int) -> Optional[Tuple[int, List[int]]]:
        """Find the path to a node by id.
        Returns (pivot_ply, [idx_top, idx_level2, ...]) where indices are 1-based sibling orders.
        """
        def _search_in_node(node: VariationNode, path: List[int]) -> Optional[List[int]]:
            for pivot_key, lst in node.children.items():
                for j, child in enumerate(lst, start=1):
                    if child.var_id == target_id:
                        return path + [j]
                    sub = _search_in_node(child, path + [j])
                    if sub:
                        return sub
            return None

        for p, lst in self.variations.items():
            for i, node in enumerate(lst, start=1):
                if node.var_id == target_id:
                    return (p, [i])
                sub = _search_in_node(node, [i])
                if sub:
                    return (p, sub)
        return None

    def add(self, pivot_ply: int, san_seq: List[str], name: Optional[str] = None,
            parent_id: Optional[int] = None, pivot_index: Optional[int] = None) -> int:
        """Add a variation.
        - If parent_id is None: add as a top-level variation at `pivot_ply`.
        - Else: add as a child of variation `parent_id` at position `pivot_index` (1-based index within parent's moves).
        Returns new var_id.
        """
        var_id = self._next_var_id
        self._next_var_id += 1
        # compute hierarchical name if not provided
        if not name:
            if parent_id is None:
                lst = self.variations.get(pivot_ply, [])
                idx = len(lst) + 1
                name = f"{pivot_ply}-{idx:02d}"
            else:
                # try to locate parent's path to compute prefix
                path_info = self._find_parent_path(parent_id)
                if path_info is None:
                    # fallback to simple name
                    name = san_seq[0] if san_seq else f"{pivot_ply}-01"
                else:
                    top_ply, indices = path_info
                    # determine new child index among siblings under given pivot_index
                    parent = self._id_map.get(parent_id)
                    sibs = []
                    if parent is not None and pivot_index is not None:
                        sibs = parent.children.get(pivot_index, [])
                    child_idx = len(sibs) + 1
                    full_indices = indices + [child_idx]
                    name = f"{pivot_ply}-" + "-".join(f"{x:02d}" for x in full_indices)
        node = VariationNode(var_id, name, list(san_seq))
        # initialize comments list aligned with moves
        node.san_comments = ["" for _ in node.san_moves]

        if parent_id is None:
            if pivot_ply not in self.variations:
                self.variations[pivot_ply] = []
            self.variations[pivot_ply].append(node)
        else:
            parent = self._id_map.get(parent_id)
            if parent is None or pivot_index is None:
                # fallback to top-level if parent not found
                if pivot_ply not in self.variations:
                    self.variations[pivot_ply] = []
                self.variations[pivot_ply].append(node)
            else:
                parent.children.setdefault(pivot_index, []).append(node)

        self._register(node, parent_id)
        return var_id

    # ---- 根据 pivot_ply 查询顶层变着 ----
    def list(self, pivot_ply: int) -> List[VariationNode]:
        return self.variations.get(pivot_ply, [])

    # ---- 全局按 id 查找节点 ----
    def find_by_id(self, var_id: int) -> Optional[VariationNode]:
        return self._id_map.get(var_id)

    # 保持兼容旧接口：接受 (pivot_ply, var_id)
    def get(self, pivot_ply: int, var_id: int) -> Optional[VariationNode]:
        return self.find_by_id(var_id)

    # --- 删除（支持顶层与任意层） ----
    def remove(self, pivot_ply: int, var_id: int) -> bool:
        node = self._id_map.get(var_id)
        if node is None:
            return False

        # Try remove from top-level
        for p, lst in list(self.variations.items()):
            before = len(lst)
            self.variations[p] = [v for v in lst if v.var_id != var_id]
            if len(self.variations[p]) != before:
                self._id_map.pop(var_id, None)
                return True

        # Otherwise search recursively in children
        def _remove_in_children(children_dict: Dict[int, List[VariationNode]]) -> bool:
            for key, lst in list(children_dict.items()):
                before = len(lst)
                children_dict[key] = [v for v in lst if v.var_id != var_id]
                if len(children_dict[key]) != before:
                    self._id_map.pop(var_id, None)
                    return True
                for v in children_dict[key]:
                    if _remove_in_children(v.children):
                        return True
            return False

        for p, lst in self.variations.items():
            for v in lst:
                if _remove_in_children(v.children):
                    return True

        return False

    # ---- Serialization ----
    def to_dict(self) -> Dict:
        def node_to_obj(node: VariationNode) -> Dict:
            return {
                "var_id": node.var_id,
                "name": node.name,
                "san_moves": list(node.san_moves),
                "san_comments": list(node.san_comments),
                "children": {str(k): [node_to_obj(ch) for ch in lst] for k, lst in node.children.items()}
            }

        out = {str(p): [node_to_obj(n) for n in lst] for p, lst in self.variations.items()}
        meta = {"next_var_id": self._next_var_id, "variations": out}
        return meta

    @classmethod
    def from_dict(cls, data: Dict) -> 'VariationManager':
        mgr = cls()
        try:
            mgr._next_var_id = int(data.get("next_var_id", mgr._next_var_id))
            raw = data.get("variations", {})

            def obj_to_node(obj: Dict) -> VariationNode:
                node = VariationNode(int(obj["var_id"]), obj.get("name", ""), list(obj.get("san_moves", [])))
                mgr._register(node)
                # load comments if present
                node.san_comments = list(obj.get("san_comments", ["" for _ in node.san_moves]))
                for k, lst in obj.get("children", {}).items():
                    idx = int(k)
                    node.children[idx] = [obj_to_node(ch) for ch in lst]
                return node

            for p_str, lst in raw.items():
                p = int(p_str)
                mgr.variations[p] = [obj_to_node(obj) for obj in lst]
        except Exception:
            # leave empty on parse error
            pass
        return mgr
