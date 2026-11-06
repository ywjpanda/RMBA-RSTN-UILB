"""Extracted definitions only. No Notebook top-level code or plotting imports."""
class LEO_env_config:

    def __init__(self, cfg):
        RED = '\x1b[91m'
        BLUE = '\x1b[94m'
        RESET = '\x1b[0m'
        BROWN = '\x1b[38;5;130m'
        print()
        print('LEOconfig 超参数')
        print(''.join(['*'] * 80))
        self.n_LEO = cfg.Zm_LEO
        self.connections = self.which_cnt(cfg.Which_Connect, cfg.Zm_LEO)
        self.validate_UnRliable_Link(cfg.UnRliable_Link)
        (self.adjacency_matrix, self.communication_list) = self.create_adjacency_matrix_and_list(self.n_LEO, self.connections.copy())
        print(f'{BROWN}LEO communication_list 为:{RESET}')
        print(self.communication_list)
        print()
        index = [i for i in range(cfg.Zm_LEO)]
        df = pd.DataFrame(self.adjacency_matrix.copy(), index=index, columns=index)
        print(f'{BROWN}LEO adjacency_matrix 为:{RESET}')
        print(df)
        print()
        print(''.join(['*'] * 80))

    def validate_UnRliable_Link(self, UnRliable_Link):
        """
        功能: 
            验证 UnRliable_Link 是否在 self.connections 中
        input: 
            UnRliable_Link - 需要验证的 tuple
        raise: ValueError - 当 UnRliable_Link 不在 self.connections 中时
        """
        if UnRliable_Link not in self.connections:
            raise ValueError(f'UnRliable_Link {UnRliable_Link} 不在 self.connections {self.connections} 中')
    '\n    which_cnt 函数\n    功能:\n        根据对应的寻找每两个卫星连接方式\n    input:\n        n: 为图形第几个\n\n    '

    def which_cnt(self, n, LEO_num):
        RESET = '\x1b[0m'
        BROWN = '\x1b[38;5;130m'
        cnt_cunchu = {0: [(0, 1)], 1: [(0, 1), (1, 2), (2, 3), (3, 0)], 2: [(0, 1), (1, 2), (2, 3)], 3: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0)], 4: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0)], 5: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 0), (1, 6), (2, 5)], 6: [(0, 1), (1, 2), (2, 3), (1, 4), (1, 6), (2, 5), (2, 7)], 7: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)], 8: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 0)], 9: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (11, 0)], 10: [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (0, 7), (1, 6), (2, 5), (6, 9), (5, 10), (4, 11)], 11: [(2, 3), (3, 4), (4, 5), (6, 7), (7, 8), (8, 9), (0, 3), (1, 4), (3, 8), (4, 7), (7, 10), (9, 11)]}
        real_cnt = cnt_cunchu[n].copy()
        if max((num for tpl in real_cnt for num in tpl)) + 1 == LEO_num:
            print(f'{BROWN}卫星连接方式为:{RESET}')
            print(real_cnt)
            print()
            return real_cnt
        else:
            raise ValueError('卫星连接方式，和定义卫星数不一致')
    '\n    create_adjacency_matrix_and_list函数\n        用途: 根据给定的卫星数量和连接关系，生成邻接矩阵和通信关系列表。\n\n        Input:\n            - nn_LEO (int): 卫星的总数量，用于定义邻接矩阵的大小。\n            - cconnections (list of tuple): 每个元组包含两个整数，表示相连卫星的编号，例如 [(0, 1), (1, 2)] 表示\n                                         卫星 0 和 1 以及卫星 1 和 2 相连。\n                                         \n        Output:\n            - aadjacency_matrix (numpy array): 邻接矩阵，大小为 (nn_LEO, nn_LEO)。矩阵中的 1 表示通信连接，0 表示未连接。\n            - ccommunication_list (list of tuple): 包含所有通信关系的列表，每个元素为一个二元组 (i, j)，表示\n                                            卫星 i 和卫星 j 之间存在通信关系。\n    '

    def create_adjacency_matrix_and_list(self, nn_LEO, cconnections):
        aadjacency_matrix = np.zeros((nn_LEO, nn_LEO), dtype=int)
        for (i, j) in cconnections:
            if i < nn_LEO and j < nn_LEO:
                aadjacency_matrix[i, j] = 1
                aadjacency_matrix[j, i] = 1
        ccommunication_list = []
        for i in range(nn_LEO):
            for j in range(nn_LEO):
                if aadjacency_matrix[i, j] == 1:
                    ccommunication_list.append((i, j))
        return (aadjacency_matrix, ccommunication_list)
    '\n    tuxinghua_LEO_cnt 函数\n        功能: 彩色打印 LEO 的 连接方式\n        input:\n            wh_nodes: cfg.Which_Connect\n            nodes = [[0, "-", 1], ["|", " ", "|"], [3, "-", 2]]\n        output:\n            无\n    '

class Task:

    def __init__(self, input_size, output_size):
        self.input_size = input_size
        self.output_size = output_size

    def __repr__(self):
        return f'Task(input_size={self.input_size}, output_size={self.output_size})'

class App_straight:

    def __init__(self, cfg):
        input_1 = random.randint(5, 30)
        output_1 = input_2 = random.randint(5, 30)
        output_2 = random.randint(5, 30)
        self.access_satellite = random.randint(0, cfg.Zm_LEO - 1)
        self.task_1 = Task(input_1, output_1)
        self.task_2 = Task(input_2, output_2)
        self.app_num = 1

    def __repr__(self):
        return f'App_straight(\n  task_1={self.task_1},\n  task_2={self.task_2},\n  access_satellite={self.access_satellite},\n  app_num={self.app_num})'

def expand_matrix(A, B):
    """
    函数名称: expand_matrix
    用途: 根据矩阵 A 的元素值，将矩阵 B 或全为 0 的矩阵填充到对应位置，生成一个新的扩展矩阵。
    
    输入:
        A (numpy array): 大小为 p*q 的矩阵，仅包含 0 和 1。
        B (numpy array): 大小为 m*n 的矩阵，用于填充 A 中对应的 1 位置。
                                     
    输出:
        expanded_matrix (numpy array): 大小为 (p*m) x (q*n) 的矩阵。A 中的 0 元素对应填充全 0 的 m*n 子矩阵，
                                       A 中的 1 元素对应填充矩阵 B。
    """
    (p, q) = A.shape
    (m, n) = B.shape
    expanded_matrix = np.zeros((p * m, q * n), dtype=B.dtype)
    for i in range(p):
        for j in range(q):
            if A[i, j] == 1:
                expanded_matrix[i * m:(i + 1) * m, j * n:(j + 1) * n] = B
    return expanded_matrix

def set_negative_to_zero(A):
    B = A.copy()
    B[B < 0] = 0
    return B

class App_straight_petri_matrix:

    def __init__(self, LEOconfig, straight_app_instance):
        tempss = 1
        temp_qian_matrix = set_negative_to_zero(self.generate_preceding_combined_matrix(LEOconfig, straight_app_instance))
        temp_hou_matrix = set_negative_to_zero(self.generate_succeeding_combined_matrix(LEOconfig, straight_app_instance))
        self.qian_matrix = copy.deepcopy(temp_qian_matrix)
        self.app_pn = copy.deepcopy(temp_hou_matrix) - copy.deepcopy(temp_qian_matrix)
    '\n    generate_preceding_run_matrix函数\n    用途: 根据给定的卫星数量和 App_straight 实例生成前置运行矩阵。\n    \n    输入:\n        n_LEO (int): 卫星的总数量，用于定义初始单位矩阵的大小。\n        straight_app_instance (App_straight): 包含 access_satellite 属性的实例。\n                                     \n    输出:\n        run_matrix (numpy array): 最终生成的前置运行矩阵，大小为 (3*n_LEO+1, 3*n_LEO+1)。\n    '

    def generate_preceding_run_matrix(self, n_LEO, straight_app_instance):
        A = np.eye(n_LEO, dtype=int)
        B = np.eye(3, dtype=int)
        C = expand_matrix(A, B)
        D = np.zeros((3 * n_LEO + 1, 3 * n_LEO + 1), dtype=int)
        D[0, 0] = 1
        D[1:, 1:] = C
        expected_size = (3 * n_LEO + 1, 3 * n_LEO + 1)
        if D.shape != expected_size:
            raise ValueError(f'矩阵 前置运行矩阵 的大小不正确! 预期: {expected_size}, 实际: {D.shape}')
        return D
    '\n    generate_preceding_run_buffer_matrix函数\n    用途: 根据给定的卫星数量和 App_straight 实例生成前置运行 buffer 矩阵。\n    \n    输入:\n        n_LEO (int): 卫星的总数量，用于定义初始单位矩阵的大小。\n        straight_app_instance (App_straight): 包含 access_satellite 属性和任务信息的实例。\n                                     \n    输出:\n        buffer_matrix (numpy array): 最终生成的前置运行 buffer 矩阵，大小为 (n_LEO, 3 * n_LEO+1)。\n    '

    def generate_preceding_run_buffer_matrix(self, n_LEO, straight_app_instance):
        identity_matrix = np.eye(n_LEO, dtype=int)
        diff_matrix = np.array([straight_app_instance.task_1.output_size - straight_app_instance.task_1.input_size, straight_app_instance.task_2.output_size - straight_app_instance.task_2.input_size, 0]).reshape(1, 3)
        expanded_matrix = expand_matrix(identity_matrix, diff_matrix)
        left_col = np.zeros((expanded_matrix.shape[0], 1), dtype=int)
        left_col[straight_app_instance.access_satellite] = straight_app_instance.task_1.input_size
        expanded_with_left = np.hstack((left_col, expanded_matrix))
        expected_size = (n_LEO, 3 * n_LEO + 1)
        if expanded_with_left.shape != expected_size:
            raise ValueError(f'矩阵 前置运行 buffer 矩阵 的大小不正确! 预期: {expected_size}, 实际: {expanded_with_left.shape}')
        return expanded_with_left
    '\n    preceding_transition_matrix函数\n    用途: 根据给定的卫星数量和通信关系列表生成前置转移矩阵。\n\n    输入:\n        - n_LEO (int): 卫星的总数量，用于定义前置转移矩阵的行数。\n        - communication_list (list of tuple): 每个元素为一个二元组 (i, j)，表示\n                                            卫星 i 和卫星 j 之间存在通信关系。\n                                     \n    输出:\n        - C (numpy array): 扩展后的前置转移矩阵，大小为 (3*n_LEO+1, 2*len(communication_list))。\n    '

    def preceding_transition_matrix(self, n_LEO, communication_list):
        transition_matrix = np.zeros((n_LEO, len(communication_list)), dtype=int)
        for (col, (i, j)) in enumerate(communication_list):
            transition_matrix[i, col] = 1
        A = np.array([[1, 0], [0, 1], [0, 0]], dtype=int)
        B = expand_matrix(transition_matrix, A)
        top_row = np.zeros((1, B.shape[1]), dtype=int)
        C = np.vstack((top_row, B))
        expected_size = (3 * n_LEO + 1, 2 * len(communication_list))
        if C.shape != expected_size:
            raise ValueError(f'矩阵 前置转移矩阵 的大小不正确! 预期: {expected_size}, 实际: {C.shape}')
        return C
    '\n    generate_preceding_transition_buffer_matrix函数\n    用途: 根据卫星数量、通信关系列表和 App_straight 实例生成前置转移 buffer 矩阵。\n\n    Input:\n        - n_LEO (int): 卫星的总数量，用于定义矩阵的行数。\n        - communication_list (list of tuple): 每个元素为一个二元组 (i, j)，表示卫星 i 和卫星 j 之间的通信。\n        - straight_app_instance (App_straight): 包含任务信息的实例。\n                                     \n    Output:\n        - buffer_matrix (numpy array): 大小为 (n_LEO, 3*len(communication_list)) 的矩阵。\n    '

    def generate_preceding_transition_buffer_matrix(self, n_LEO, communication_list, straight_app_instance):
        A = np.zeros((n_LEO, len(communication_list)), dtype=int)
        for (col, (i, j)) in enumerate(communication_list):
            A[j, col] = 1
        B = np.array([straight_app_instance.task_1.input_size, straight_app_instance.task_1.output_size]).reshape(1, 2)
        expanded_matrix = expand_matrix(A, B)
        expected_size = (n_LEO, 2 * len(communication_list))
        if expanded_matrix.shape != expected_size:
            raise ValueError(f'矩阵 前置转移 buffer 矩阵 的大小不正确! 预期: {expected_size}, 实际: {expanded_matrix.shape}')
        return expanded_matrix
    '\n    generate_preceding_combined_matrix函数\n    用途: 生成一个前置矩阵。\n    \n    输入:\n        LEOconfig: 包含 n_LEO 和 communication_list 属性的配置对象。\n        straight_app_instance (App_straight): 包含任务信息的实例。\n                                     \n    输出:\n        Qian_matrix (numpy array): 最终生成的组合矩阵，大小为 (4*n_LEO+2, 3*n_LEO+1+2*len(communication_list))。\n    '

    def generate_preceding_combined_matrix(self, LEOconfig, straight_app_instance):
        n_LEO = LEOconfig.n_LEO
        communication_list = LEOconfig.communication_list
        QUL = self.generate_preceding_run_matrix(n_LEO, straight_app_instance)
        QUR = self.preceding_transition_matrix(n_LEO, communication_list)
        if QUL.shape[0] != QUR.shape[0]:
            raise ValueError(f'QUL 和 QUR 的行数不相同! QUL行数: {QUL.shape[0]}, QUR行数: {QUR.shape[0]}')
        QU = np.hstack((QUL, QUR))
        bottom_row = np.zeros((1, QU.shape[1]), dtype=int)
        Big_QU = np.vstack((QU, bottom_row))
        QLL = self.generate_preceding_run_buffer_matrix(n_LEO, straight_app_instance)
        QLR = self.generate_preceding_transition_buffer_matrix(n_LEO, communication_list, straight_app_instance)
        if QLL.shape[0] != QLR.shape[0]:
            raise ValueError(f'QLL 和 QLR 的行数不相同! QLL行数: {QLL.shape[0]}, QLR行数: {QLR.shape[0]}')
        QL = np.hstack((QLL, QLR))
        if Big_QU.shape[1] != QL.shape[1]:
            raise ValueError(f'Big_QU 和 QL 的列数不相同! Big_QU列数: {Big_QU.shape[1]}, QL列数: {QL.shape[1]}')
        Qian_matrix = np.vstack((Big_QU, QL))
        expected_size = (4 * n_LEO + 2, 3 * n_LEO + 1 + 2 * len(communication_list))
        if Qian_matrix.shape != expected_size:
            raise ValueError(f'Qian_matrix 的大小不正确! 预期: {expected_size}, 实际: {Qian_matrix.shape}')
        return Qian_matrix
    '\n    [test_stright_matrix.ipynb#generate_succeeding_run_matrix]\n    函数名称: generate_succeeding_run_matrix\n    用途: 根据卫星数量和 App_straight 实例生成后置运行矩阵。\n    \n    输入:\n        n_LEO (int): 卫星的总数量。\n        straight_app_instance (App_straight): 包含 access_satellite 属性的实例。\n                                     \n    输出:\n        E (numpy array): 最终生成的后置运行矩阵，大小为 (3*n_LEO+1, 3*n_LEO+1)。\n    '

    def generate_succeeding_run_matrix(self, n_LEO, straight_app_instance):
        A = np.eye(n_LEO, dtype=int)
        B = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=int)
        C = expand_matrix(A, B)
        bottom_row = np.array([[1 if j % 3 == 2 else 0 for j in range(C.shape[1])]], dtype=int)
        D = np.vstack((C, bottom_row))
        left_col = np.zeros((D.shape[0], 1), dtype=int)
        left_col[straight_app_instance.access_satellite * 3, 0] = 1
        E = np.hstack((left_col, D))
        expected_size = (3 * n_LEO + 1, 3 * n_LEO + 1)
        if E.shape != expected_size:
            raise ValueError(f'矩阵 E 的大小不正确! 预期: {expected_size}, 实际: {E.shape}')
        return E
    '\n    函数名称: generate_succeeding_run_buffer_matrix\n    用途: 根据卫星数量和 App_straight 实例生成后置运行 buffer 矩阵。\n    \n    输入:\n        n_LEO (int): 卫星的总数量。\n        straight_app_instance (App_straight): 包含任务信息和接入卫星信息的实例。\n                                     \n    输出:\n        succeeding_run_buffer_matrix (numpy array): 最终生成的后置运行 buffer 矩阵，大小为 (n_LEO, 2*n_LEO+2)。\n    '

    def generate_succeeding_run_buffer_matrix(self, n_LEO, straight_app_instance):
        identity_matrix = np.eye(n_LEO, dtype=int)
        diff_matrix = np.array([straight_app_instance.task_1.input_size - straight_app_instance.task_1.output_size, straight_app_instance.task_2.input_size - straight_app_instance.task_2.output_size, straight_app_instance.task_2.output_size]).reshape(1, 3)
        expanded_matrix = expand_matrix(identity_matrix, diff_matrix)
        left_col = np.zeros((expanded_matrix.shape[0], 1), dtype=int)
        expanded_with_left_col = np.hstack((left_col, expanded_matrix))
        expected_size = (n_LEO, 3 * n_LEO + 1)
        if expanded_with_left_col.shape != expected_size:
            raise ValueError(f'矩阵 expanded_with_left_col 的大小不正确! 预期: {expected_size}, 实际: {expanded_with_left_col.shape}')
        return expanded_with_left_col
    '\n    函数名称: succeeding_transition_matrix\n    用途: 根据给定的卫星数量和通信关系列表生成后置转移矩阵。\n    \n    Input:\n        - n_LEO (int): 卫星的总数量，用于定义矩阵的行数。\n        - communication_list (list of tuple): 每个元素为一个二元组 (i, j)，表示\n                                            卫星 i 和卫星 j 之间存在通信关系。\n                                     \n    Output:\n        - transition_matrix (numpy array): 后置转移矩阵，大小为 (n_LEO, len(communication_list))。\n                                         如果行的索引等于通信元组的第二个元素，则对应位置为 1，否则为 0。\n    '

    def succeeding_transition_matrix(self, n_LEO, communication_list):
        transition_matrix = np.zeros((n_LEO, len(communication_list)), dtype=int)
        for (col, (i, j)) in enumerate(communication_list):
            transition_matrix[j, col] = 1
        A = np.array([[1, 0], [0, 1], [0, 0]], dtype=int)
        B = expand_matrix(transition_matrix, A)
        bottom_row = np.zeros((1, B.shape[1]), dtype=int)
        C = np.vstack((B, bottom_row))
        expected_size = (3 * n_LEO + 1, 2 * len(communication_list))
        if C.shape != expected_size:
            raise ValueError(f'矩阵 后置转移矩阵 的大小不正确! 预期: {expected_size}, 实际: {C.shape}')
        return C
    '\n    函数名称: generate_succeeding_transition_buffer_matrix\n    用途: 根据卫星数量、通信关系列表和 App_straight 实例生成后置转移 buffer 矩阵。\n    \n    输入:\n        n_LEO (int): 卫星的总数量。\n        communication_list (list of tuple): 每个元素为一个二元组 (i, j)，表示卫星 i 和卫星 j 之间的通信。\n        straight_app_instance (App_straight): 包含任务信息的实例。\n                                     \n    输出:\n        succeeding_transition_buffer_matrix (numpy array): 最终生成的后置转移 buffer 矩阵，大小为 (n_LEO, 3*len(communication_list))。\n    '

    def generate_succeeding_transition_buffer_matrix(self, n_LEO, communication_list, straight_app_instance):
        A = np.zeros((n_LEO, len(communication_list)), dtype=int)
        for (col, (i, j)) in enumerate(communication_list):
            A[i, col] = 1
        B = np.array([straight_app_instance.task_1.input_size, straight_app_instance.task_1.output_size]).reshape(1, 2)
        expanded_matrix = expand_matrix(A, B)
        return expanded_matrix
    '\n    [test_stright_matrix.ipynb#generate_succeeding_combined_matrix]\n    函数名称: generate_succeeding_combined_matrix\n    用途: 生成后置组合矩阵，结合转移矩阵、运行矩阵和 buffer 矩阵。\n    \n    输入:\n        LEOconfig: 包含 n_LEO 和 communication_list 属性的配置对象。\n        straight_app_instance (App_straight): 包含任务信息的实例。\n                                     \n    输出:\n        Hou_matrix (numpy array): 最终生成的后置组合矩阵，大小为 (4*n_LEO+2, 3*n_LEO+1+2*len(communication_list))。\n    '

    def generate_succeeding_combined_matrix(self, LEOconfig, straight_app_instance):
        n_LEO = LEOconfig.n_LEO
        communication_list = LEOconfig.communication_list
        QUL = self.generate_succeeding_run_matrix(n_LEO, straight_app_instance)
        QUR = self.succeeding_transition_matrix(n_LEO, communication_list)
        if QUL.shape[0] != QUR.shape[0]:
            raise ValueError(f'QUL 和 QUR 的行数不相同! QUL行数: {QUL.shape[0]}, QUR行数: {QUR.shape[0]}')
        QU = np.hstack((QUL, QUR))
        top_row = np.zeros((1, QU.shape[1]), dtype=int)
        Big_QU = np.vstack((top_row, QU))
        QLL = self.generate_succeeding_run_buffer_matrix(n_LEO, straight_app_instance)
        QLR = self.generate_succeeding_transition_buffer_matrix(n_LEO, communication_list, straight_app_instance)
        if QLL.shape[0] != QLR.shape[0]:
            raise ValueError(f'QLL 和 QLR 的行数不相同! QLL行数: {QLL.shape[0]}, QLR行数: {QLR.shape[0]}')
        QL = np.hstack((QLL, QLR))
        if Big_QU.shape[1] != QL.shape[1]:
            raise ValueError(f'Big_QU 和 QL 的列数不相同! Big_QU列数: {Big_QU.shape[1]}, QL列数: {QL.shape[1]}')
        Hou_matrix = np.vstack((Big_QU, QL))
        expected_size = (4 * n_LEO + 2, 3 * n_LEO + 1 + 2 * len(communication_list))
        if Hou_matrix.shape != expected_size:
            raise ValueError(f'Hou_matrix 的大小不正确! 预期: {expected_size}, 实际: {Hou_matrix.shape}')
        return Hou_matrix

def find_all_disconnect_trans(LEOconfig, cfg):
    """
    函数名称: find_all_disconnect_trans
    用途: 找出在 Unreliable Link 断开时，不能触发的 transitions。
    
    输入: 
        LEOconfig: 卫星参数，包含 communication_list 和 n_LEO 等属性。
        cfg: 系统参数，包含 UnRliable_Link 属性（一个长度为2的tuple）。
                                      
    输出: 
        disc_trans_tuple: 长度为4的tuple，表示在 Unreliable Link 断开时不能触发的 transitions。
    """
    temp_cl = copy.deepcopy(LEOconfig.communication_list)
    temp_cl_double = []
    for item in temp_cl:
        temp_cl_double.append(item)
        temp_cl_double.append(item)
    temp_URL = copy.deepcopy(cfg.UnRliable_Link)
    temp_URL_re = (temp_URL[1], temp_URL[0])
    temp_xtrans = []
    for (idx, item) in enumerate(temp_cl_double):
        if item == temp_URL or item == temp_URL_re:
            temp_xtrans.append(idx)
    temp_xtrans.sort()
    offset = 3 * LEOconfig.n_LEO + 1
    disc_trans = [x + offset for x in temp_xtrans]
    if len(disc_trans) == 4:
        return tuple(disc_trans)
    else:
        raise ValueError('disc_trans must have 4 elements')
