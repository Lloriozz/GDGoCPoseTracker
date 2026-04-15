import pickle
from sklearn.tree._tree import Tree
import numpy as np
import glob
import os

class TreeMock:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
    
    def __setstate__(self, state):
        self.state = state

class CustomUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == 'sklearn.tree._tree' and name == 'Tree':
            return TreeMock
        return super().find_class(module, name)

new_dtype = np.dtype([
    ('left_child', '<i8'),
    ('right_child', '<i8'),
    ('feature', '<i8'),
    ('threshold', '<f8'),
    ('impurity', '<f8'),
    ('n_node_samples', '<i8'),
    ('weighted_n_node_samples', '<f8'),
    ('missing_go_to_left', 'u1')
])

def patch_tree(tree_mock):
    state = tree_mock.state
    old_nodes = state['nodes']
    
    new_nodes = np.zeros(old_nodes.shape, dtype=new_dtype)
    for name in old_nodes.dtype.names:
        new_nodes[name] = old_nodes[name]
    
    state['nodes'] = new_nodes
    
    real_tree = Tree.__new__(Tree, *tree_mock.args, **tree_mock.kwargs)
    real_tree.__setstate__(state)
    return real_tree

def replace_tree_mocks(obj, memo=None):
    if memo is None:
        memo = {}
    obj_id = id(obj)
    if obj_id in memo:
        return memo[obj_id]

    if isinstance(obj, TreeMock):
        new_tree = patch_tree(obj)
        memo[obj_id] = new_tree
        return new_tree

    memo[obj_id] = obj
    
    if isinstance(obj, list):
        for i, val in enumerate(obj):
            obj[i] = replace_tree_mocks(val, memo)
    elif isinstance(obj, tuple):
        new_tuple = tuple(replace_tree_mocks(val, memo) for val in obj)
        memo[obj_id] = new_tuple
        return new_tuple
    elif isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[replace_tree_mocks(k, memo)] = replace_tree_mocks(v, memo)
    elif hasattr(obj, '__dict__'):
        for k, v in obj.__dict__.items():
            setattr(obj, k, replace_tree_mocks(v, memo))
    
    return obj

def main():
    for pkl_file in glob.glob('server/static/model/*.pkl'):
        # Skip scaler models if they are fine, but trying to patch won't hurt
        print(f"Processing {pkl_file}...")
        try:
            with open(pkl_file, 'rb') as f:
                model = CustomUnpickler(f).load()
            
            model = replace_tree_mocks(model)
            
            with open(pkl_file, 'wb') as f:
                pickle.dump(model, f)
            print(" -> Patched successfully")
        except Exception as e:
            print(f" -> Error or no patch needed: {e}")

if __name__ == '__main__':
    main()
