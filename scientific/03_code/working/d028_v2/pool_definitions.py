"""Extracted definitions only. No Notebook top-level code or plotting imports."""
class ValueCountingDict(dict):
    """
    一个可以自动统计指定 value 数量的字典。

    例如 counted_value=1 时，
    self.counted_value_num 会自动记录当前字典中 value == 1 的 key 数量。
    """

    def __init__(self, *args, counted_value=1, **kwargs):
        super().__init__()
        self.counted_value = counted_value
        self.counted_value_num = 0
        if args or kwargs:
            self.update(*args, **kwargs)

    def __setitem__(self, key, value):
        """
        每次执行 dict[key] = value 时，自动更新 counted_value_num。
        """
        if key in self and self[key] == self.counted_value:
            self.counted_value_num -= 1
        super().__setitem__(key, value)
        if value == self.counted_value:
            self.counted_value_num += 1

    def update(self, *args, **kwargs):
        """
        保证使用 update() 写入时，也能正确维护 counted_value_num。
        """
        other = dict(*args, **kwargs)
        for (key, value) in other.items():
            self[key] = value

class App_Collection:
    """
    reset 函数
        重新生成所有的参数。
        没有输入。
    
    """
    '\n    reset 函数\n        重新生成所有的参数。\n        没有输入。\n    \n    '

    def generate_pn(self):
        for i in range(self.app_number):
            straight_app_instance = self.app_for_tasks[i]
            straight_app_pn = App_straight_petri_matrix(LEOconfig, straight_app_instance)
            self.app_pn_for_qianzhi_matrix.append(copy.deepcopy(straight_app_pn.qian_matrix))
            self.app_pn_for_pn_matrix.append(copy.deepcopy(straight_app_pn.app_pn))
    '\n    generate_app_task_size_numpy函数\n    目的:\n        生成一个包含所有task的input和output size以方便查找\n        还包含access satellite\n\n    输出:\n        更新self.app_task_size_access_sate\n    '

    def generate_app_task_size_numpy(self):
        rec_app_task_size_access_sate = np.empty((0, 5), dtype=np.int32)
        for i in range(self.app_number):
            temp_app = self.app_for_tasks[i]
            temp_rec = np.array([temp_app.task_1.input_size, temp_app.task_2.input_size, temp_app.task_2.input_size, temp_app.task_2.output_size, temp_app.access_satellite])
            rec_app_task_size_access_sate = np.vstack((rec_app_task_size_access_sate, temp_rec))
        self.app_task_size_access_sate = copy.deepcopy(rec_app_task_size_access_sate)
    '\n    one_marking_length_record 函数\n    功能: 记录marking中所有app的长度。\n    input:\n        jl_mark: 一个初始化marking，长度是所有app+LEO buffer。\n    output:\n        一个列表，列表中的每个元素对应输入列表中每个一维 NumPy 数组的长度。\n    '

    def marking_length_jilu(self, jl_mark_in):
        jl_mark = copy.deepcopy(jl_mark_in)
        length_list = []
        for arr in jl_mark:
            length_list.append(len(arr))
        return length_list
    '\n    功能: \n        给到起始marking，找到初始化marking。\n        初始化marking是所有单独的app，分别完成1个到所有的。\n    input:\n        无。但是实际上用的是 self.app_marking_without_buffer\n        am_wo_b_in: 一个列表，里面包含多个一维整数 numpy 数组，且每个数组的第 0 个元素为大于 0 的整数，其余元素为 0。\n    output:\n        一个 初始化 safe marking 集合。\n    '

    def Initial_safe_markings(self):
        am_wo_b = self.app_marking_without_buffer.copy()
        app_sate_marking_jihe = set()
        all_combinations = []
        for arr in am_wo_b:
            first_value = arr[0]
            valid_combos = []
            for i in range(first_value + 1):
                valid_combos.append((i, first_value - i))
            all_combinations.append(valid_combos)
        for combo in product(*all_combinations):
            new_am_wo_b = []
            for (i, (first, last)) in enumerate(combo):
                new_arr = am_wo_b[i].copy()
                new_arr[0] = first
                if len(new_arr) > 1:
                    new_arr[-1] = last
                new_am_wo_b.append(new_arr)
            new_am_wo_b.append(self.p_LEO.copy())
            new_am_wo_b_2 = copy.deepcopy(new_am_wo_b)
            new_am_wo_b.append(np.array([1, 0]))
            new_am_wo_b_2.append(np.array([0, 1]))
            new_tp_mark = self.decompose_marking_to_tuple(new_am_wo_b)
            new_tp_mark_2 = self.decompose_marking_to_tuple(new_am_wo_b_2)
            if new_tp_mark not in app_sate_marking_jihe and new_tp_mark not in self.all_safe_marking_set:
                self.all_safe_marking_list.append(new_am_wo_b)
                app_sate_marking_jihe.add(new_tp_mark)
            if new_tp_mark_2 not in app_sate_marking_jihe and new_tp_mark_2 not in self.all_safe_marking_set:
                self.all_safe_marking_list.append(new_am_wo_b_2)
                app_sate_marking_jihe.add(new_tp_mark_2)
        dd = self.app_number_record.copy()
        dd += 1
        if len(self.all_safe_marking_list) == np.prod(dd) * 2:
            self.initial_safe_marking_num = len(self.all_safe_marking_list)
            self.initial_safe_marking_list = copy.deepcopy(self.all_safe_marking_list)
        else:
            raise ValueError('初始化safe markings 的时候 list 数量 不怎么对')
        if len(app_sate_marking_jihe) == np.prod(dd) * 2:
            return app_sate_marking_jihe
        else:
            raise ValueError('初始化safe markings 的时候不怎么对')
    '\n    decompose_marking_to_tuple 函数\n    功能: 将输入marking合并成一个一维的元组。\n    input:\n        jl_mark: 一个marking，长度是所有app+LEO buffer。\n    output:\n        一个一维的元组，该元组由输入列表中所有一维 NumPy 数组的元素依次合并而成。\n    '

    def decompose_marking_to_tuple(self, jl_mark_in):
        jl_mark = jl_mark_in.copy()
        tp_mark = tuple((tuple(arr.tolist()) for arr in jl_mark))
        total_length = 0
        for tup in tp_mark:
            total_length += len(tup)
        if total_length == sum(self.one_marking_length_record):
            return tp_mark
        else:
            raise ValueError('组合的marking长度不对。')
    '\n    generate_specific_apps 函数\n    功能:\n        生成指定数量的 直线 app 和 分解合并 app\n        只生成任务\n    input:\n        qian_zd_app_num -> list 指定前面特定app的数量以及类型 \n        \n    '
    '\n    generate_one_straight_app 函数\n    功能: 生成一个指定的straight app\n    App_straight(\n        task_1=Task(input_size=16, output_size=18),\n        task_2=Task(input_size=18, output_size=27),\n        access_satellite=1,\n        app_num=1)\n    输入:\n        dijige: 整数，指定第几个app\n        shuru: list，6位，分别指代 [16,18,18,27,1,1]\n            0. task_1.input\n            1. task_1.output_size\n            2. task_2.input_size\n            3. task_2.output_size\n            4. access_satellite\n            5. app_num\n    输出:\n        无\n        \n    '

    def generate_one_straight_app(self, dijige, shuru):
        self.app_for_tasks[dijige].task_1.input_size = shuru[0]
        self.app_for_tasks[dijige].task_1.output_size = shuru[1]
        self.app_for_tasks[dijige].task_2.input_size = shuru[2]
        self.app_for_tasks[dijige].task_2.output_size = shuru[3]
        self.app_for_tasks[dijige].access_satellite = shuru[4]
        self.app_for_tasks[dijige].app_num = shuru[5]
        if shuru[1] != shuru[2]:
            raise ValueError('task_1.output_size 不能等于 task_2.input_size')
        if shuru[4] >= cfg.Zm_LEO:
            raise ValueError('access_satellite 不能大于 卫星数量')
        if dijige >= cfg.Zn_App:
            raise ValueError('app_num 不能大于 应用数量')
    '\n    generate_spc_apps_markings 函数\n    功能:\n        生成app对应marking\n    \n    \n    '

    def generate_spc_apps_markings(self):
        self.app_marking_without_buffer = []
        app_num_rec = []
        for n in range(self.app_number):
            m0 = np.zeros((1, LEOconfig.n_LEO * 3 + 2), dtype=int)[0]
            m0[0] = self.app_for_tasks[n].app_num
            app_num_rec.append(self.app_for_tasks[n].app_num)
            self.app_marking_without_buffer.append(m0)
        self.app_number_record = np.array(app_num_rec).copy()
    '\n    jiance_weiwancheng_app_from_marking 函数\n    功能: \n        从输入列表中截取除最后一个数组外的其他数组，然后取这些数组的最后一个值，合成一个新的一维 numpy 数组。\n    input:\n        jl_mark_in: 一个列表，里面包含了多个长短不同的一维 numpy 数组。\n    output:\n        一个一维 numpy 数组，由 jl_mark 中每个 numpy 数组的最后一个值组成。\n    '

    def jiance_weiwancheng_app_from_marking(self, jl_mark_in):
        if len(jl_mark_in) != self.app_number + 2:
            raise ValueError('检测完成marking函数输入不正确')
        jl_mark = copy.deepcopy(jl_mark_in)[:-2]
        last_values = []
        for arr in jl_mark:
            if len(arr) > 0:
                last_values.append(arr[-1])
        result = np.array(last_values)
        return result
    '\n        功能: 找出两个相同长度的 NumPy 数组中值不相同的元素的索引。\n        input:\n            arr1: self.app_number_record\n            arr2: self.app_complete\n        output:\n            一个 NumPy 数组，包含两个输入数组中值不相同的元素的索引。\n            哪个app还没有完成\n    '

    def get_notdone_app(self, arr1_in, arr2_in):
        arr1 = arr1_in.copy()
        arr2 = arr2_in.copy()
        if arr1.shape[0] != arr2.shape[0]:
            raise ValueError('两个输入数组的长度必须相同。')
        different_mask = arr1 != arr2
        different_indices = np.where(different_mask)[0]
        return different_indices
    '\n    check_marking_len函数\n    目的：\n        检查一个marking的长度是否正确\n        marking的长度包含buffer\n    \n    输入：\n        app_leixing: 0为straight，1为manu\n        \n    输出：\n        bool: Ture or False\n    '

    def check_marking_len(self, m_in, LEOconfig, app_leixing):
        m = m_in.copy()
        if app_leixing == 0:
            a = 4
        len_m = a * LEOconfig.n_LEO + 2
        return len(m) == len_m
    '\n    find_possible_trnas函数\n    目的：\n        找到 marking 中可以执行的transition。\n\n    参数:\n        m: 一个marking。\n        I: 前置矩阵。\n        LEOconfig: 包含 n_LEO 属性的配置对象。\n\n    Output:\n        indices: 不算buffer可能触发的trans\n        exe_indices: 算上buffer实际可触发的trans\n    '

    def find_possible_trnas(self, m_in, I_in, LEOconfig, unrel_link_in):
        m = copy.deepcopy(m_in)
        I = copy.deepcopy(I_in)
        q = len(m)
        unrel_link = unrel_link_in.copy()
        indices = []
        exe_indices = []
        for n in range(I.shape[1]):
            if np.all(m >= I[:, n]):
                if unrel_link[0] == 0:
                    if n not in cfg.DISCONNECT_TRANS:
                        exe_indices.append(n)
                else:
                    exe_indices.append(n)
        return (indices, exe_indices)
    '\n    change_unreal_link_marking 函数\n    功能:\n        将输入marking的link切换\n    input:\n        marking_in: 输入的marking\n    output:\n        next_marking\n    \n    '

    def change_unreal_link_marking(self, marking_in):
        next_marking = copy.deepcopy(marking_in)
        dangqian_unrel_link = next_marking[-1].copy()
        if dangqian_unrel_link[0] == 0:
            next_unrel_link = np.array([1, 0])
        else:
            next_unrel_link = np.array([0, 1])
        next_marking[-1] = next_unrel_link
        return next_marking
    '\n    将输入的元组转换为包含NumPy数组的列表。\n    \n    参数:\n        mk_tp_in (tuple): 包含多个子元组的元组\n    \n    返回:\n        list: 包含NumPy数组的列表，每个数组对应原元组中的一个子元组\n    '

    def decompose_tuple_to_marking(self, mk_tp_in):
        mk_tp = copy.deepcopy(mk_tp_in)
        mk_yb = [np.array(sub_tuple) for sub_tuple in mk_tp]
        if self.decompose_marking_to_tuple(mk_yb) == mk_tp_in:
            return mk_yb
        else:
            raise ValueError('转换 tuple to marking 错误')
    '\n    generate_end_marking函数\n    目的：\n        生成所有的结束marking list 和 set\n    \n    输入：\n        无\n    \n    输出：\n        一个列表，包含所有的结束marking\n    \n\n    '

    def generate_end_marking(self):
        result = copy.deepcopy(self.app_start_marking_with_buffer)
        for i in range(len(result) - 2):
            qishi = result[i][0]
            result[i][0] = 0
            result[i][-1] = qishi
        self.correct_end_marking_list.append(result)
        self.correct_end_marking_set.add(self.decompose_marking_to_tuple(result))
        result_2 = self.change_unreal_link_marking(copy.deepcopy(result))
        self.correct_end_marking_list.append(result_2)
        self.correct_end_marking_set.add(self.decompose_marking_to_tuple(result_2))
    '\n    find_all_markings函数\n    目的：\n        找到所有的marking\n\n    输入：\n        无\n\n    输出：\n        self.suoyoude_marking_list\n        self.suoyoude_marking_set\n        self.suoyoude_marking_length\n    '
    '\n    find_next_marking_list 函数\n    功能:\n        寻找当前marking下，能触发到达的下一个 marking\n\n    input:\n        ini_marking_in: 输入的marking\n\n    output:\n        xiayige_marking_list: 能触发到达marking的list\n\n    '

    def find_next_marking_list(self, ini_marking_in):
        nm_trans = []
        xiayige_marking_list = []
        ini_marking = copy.deepcopy(ini_marking_in)
        whichapp_notdone = self.get_notdone_app(self.jiance_weiwancheng_app_from_marking(ini_marking), self.app_number_record).copy()
        which_app_nd_rd = self.random_a_nporlist(whichapp_notdone)
        which_app_nd_rd
        uln = ini_marking[-1].copy()
        for wand in which_app_nd_rd:
            m_0 = ini_marking[wand].copy()
            p_LEO = ini_marking[-2].copy()
            m_now = np.hstack((m_0, p_LEO))
            (_, kechufa_trans) = self.find_possible_trnas(m_now, self.app_pn_for_qianzhi_matrix[wand], LEOconfig, uln)
            if len(kechufa_trans) > 0:
                for t in kechufa_trans:
                    chufa_t = [wand, t]
                    nm_trans.append(chufa_t)
        nm_trans_random = self.random_a_nporlist(nm_trans)
        for shiji_t in nm_trans_random:
            temp_marking = self.exe_one_trans(ini_marking, shiji_t[0], shiji_t[1])
            xiayige_marking_list.append(temp_marking)
        temp_change_link_marking = self.change_unreal_link_marking(ini_marking)
        xiayige_marking_list.insert(0, temp_change_link_marking)
        return xiayige_marking_list
    '\n    random_a_nporlist函数:\n        此函数用于随机打乱输入的列表或 numpy 数组的顺序。\n    \n    Input:\n        input_data (list or numpy.ndarray): 输入的列表或 numpy 数组。\n    \n    Output:\n        与输入类型相同、长度相同但元素顺序随机打乱的对象。\n    \n    功能:\n        接收一个列表或 numpy 数组作为输入，随机打乱其元素顺序后返回相同类型的对象。\n    '

    def random_a_nporlist(self, input_data):
        if isinstance(input_data, np.ndarray):
            shuffled = input_data.copy()
            np.random.shuffle(shuffled)
            return shuffled
        elif isinstance(input_data, list):
            shuffled = input_data.copy()
            random.shuffle(shuffled)
            return shuffled
        else:
            raise ValueError('输入应为列表或 numpy 数组。')
    '\n    exe_one_trans 函数\n    功能:\n        在一个marking下执行一个trans，然后看下一个marking是什么\n    input:\n        one_marking_in: 执行前的marking\n        nyg_app: 要执行的app是哪一个\n        nyg_trans: 要执行的trans是哪一个\n\n    '

    def exe_one_trans(self, one_marking_in, nyg_app, nyg_trans):
        if nyg_app > self.app_number or nyg_trans > self.app_pn_for_qianzhi_matrix[nyg_app].shape[1]:
            raise ValueError('在执行一个trans的时候，输入不对')
        ttxianzaide_marking = copy.deepcopy(one_marking_in)
        ttm_0 = ttxianzaide_marking[nyg_app]
        ttp_LEO = ttxianzaide_marking[-2]
        ttm_now = np.hstack((ttm_0, ttp_LEO))
        ttpn_matrix = self.app_pn_for_pn_matrix[nyg_app].copy()
        ttm_next = ttm_now.copy() + ttpn_matrix[:, nyg_trans].copy()
        asxin_marking = copy.deepcopy(ttxianzaide_marking)
        asxin_marking[nyg_app] = ttm_next[:-LEOconfig.n_LEO].copy()
        asxin_marking[-2] = ttm_next[-LEOconfig.n_LEO:].copy()
        return asxin_marking
    '"\n    robust_nbba_pandaun 函数\n    功能:\n        判断一个 marking 是否为 safe, incomplete, deadlock\n    \n    input:\n        当前走到哪的marking\n    \n    output:\n        对于 连接marking [1,0] 有3种:\n            -2: incomplete\n            -1: deadlock\n             1: safe\n        对于 断开marking [0,1] 有2种:\n            -1: deadlock\n             1: safe\n    \n    '

    def robust_nbba_pandaun(self, ini_marking_in, jilu_suoyoude_marking_safeornot):
        ini_marking = copy.deepcopy(ini_marking_in)
        ini_marking_tuple = self.decompose_marking_to_tuple(ini_marking)
        this_marking_safeornot = 0
        dangqian_UNREL_link = ini_marking[-1][0]
        if ini_marking_tuple in jilu_suoyoude_marking_safeornot:
            this_marking_safeornot = jilu_suoyoude_marking_safeornot[ini_marking_tuple]
            return this_marking_safeornot
        else:
            flag_1 = 0
            (flag_1, final_route_total_trans_1) = self.panduan_chaoji_one_marking_sorn(ini_marking)
            if dangqian_UNREL_link == 1:
                duankai_makring = self.change_unreal_link_marking(ini_marking)
                duankai_marking_tuple = self.decompose_marking_to_tuple(duankai_makring)
                if duankai_marking_tuple in jilu_suoyoude_marking_safeornot:
                    duankai_marking_state = jilu_suoyoude_marking_safeornot[duankai_marking_tuple]
                    if flag_1 == 1 and duankai_marking_state == -1:
                        this_marking_safeornot = -2
                        jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                        return this_marking_safeornot
                    elif flag_1 == 1 and duankai_marking_state == 1:
                        this_marking_safeornot = 1
                        jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                        return this_marking_safeornot
                    elif flag_1 == 0 and duankai_marking_state == -1:
                        this_marking_safeornot = -1
                        jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                        return this_marking_safeornot
                    else:
                        raise ValueError('flag_1 and duankai_marking_state are not valid')
                else:
                    flag_2 = 0
                    (flag_2, final_route_total_trans_2) = self.panduan_chaoji_one_marking_sorn(duankai_makring)
                    if flag_1 == 1 and flag_2 == 1:
                        self.add_lujing_safe_marking_in_dict(ini_marking, final_route_total_trans_2, jilu_suoyoude_marking_safeornot)
                        jilu_suoyoude_marking_safeornot[duankai_marking_tuple] = 1
                        this_marking_safeornot = 1
                        jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                        return this_marking_safeornot
                    elif flag_1 == 1 and flag_2 == 0:
                        jilu_suoyoude_marking_safeornot[duankai_marking_tuple] = -1
                        this_marking_safeornot = -2
                        jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                        return this_marking_safeornot
                    elif flag_1 == 0 and flag_2 == 0:
                        jilu_suoyoude_marking_safeornot[duankai_marking_tuple] = -1
                        this_marking_safeornot = -1
                        jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                        return this_marking_safeornot
                    else:
                        raise ValueError('flag_1 and flag_2 are not valid')
            elif dangqian_UNREL_link == 0:
                lianjie_marking = self.change_unreal_link_marking(ini_marking)
                lianjie_marking_tuple = self.decompose_marking_to_tuple(lianjie_marking)
                if flag_1 == 1:
                    this_marking_safeornot = 1
                    self.add_lujing_safe_marking_in_dict(lianjie_marking, final_route_total_trans_1, jilu_suoyoude_marking_safeornot)
                    return this_marking_safeornot
                elif flag_1 == 0:
                    this_marking_safeornot = -1
                    jilu_suoyoude_marking_safeornot[ini_marking_tuple] = this_marking_safeornot
                    if lianjie_marking_tuple in jilu_suoyoude_marking_safeornot:
                        return this_marking_safeornot
                    else:
                        (flag_2, _) = self.panduan_chaoji_one_marking_sorn(lianjie_marking)
                        if flag_2 == 1:
                            jilu_suoyoude_marking_safeornot[lianjie_marking_tuple] = -2
                            return this_marking_safeornot
                        elif flag_2 == 0:
                            jilu_suoyoude_marking_safeornot[lianjie_marking_tuple] = -1
                            return this_marking_safeornot
                        else:
                            raise ValueError('在断开时，flag_2 is not valid')
            else:
                raise ValueError('dangqian_UNREL_link is not valid')
    '\n    find_next_marking_list 函数\n    功能:\n        寻找当前marking下，能触发到达的下一个 marking\n\n    input:\n        ini_marking_in: 输入的marking\n\n    output:\n        xiayige_marking_list: 能触发到达marking的list\n\n    '

    def get_enabled_transitions(self, ini_marking_in):
        nm_trans = []
        ini_marking = copy.deepcopy(ini_marking_in)
        whichapp_notdone = self.get_notdone_app(self.jiance_weiwancheng_app_from_marking(ini_marking), self.app_number_record).copy()
        which_app_nd_rd = self.random_a_nporlist(whichapp_notdone)
        which_app_nd_rd
        uln = ini_marking[-1].copy()
        for wand in which_app_nd_rd:
            m_0 = ini_marking[wand].copy()
            p_LEO = ini_marking[-2].copy()
            m_now = np.hstack((m_0, p_LEO))
            (_, kechufa_trans) = self.find_possible_trnas(m_now, self.app_pn_for_qianzhi_matrix[wand], LEOconfig, uln)
            if len(kechufa_trans) > 0:
                for t in kechufa_trans:
                    chufa_t = [wand, t]
                    nm_trans.append(chufa_t)
        nm_trans_random = self.random_a_nporlist(nm_trans)
        return nm_trans_random
    '\n    panduan_chaoji_one_marking_sorn 函数 \n    功能:\n        判断一个marking 是不是 safe 的\n\n    input:\n        makring\n\n    output:\n        this_marking_safeornot: 1 为 safe, 0 为 unsafe\n        execution_time: 判断一个makring 的时间\n    '

    def panduan_chaoji_one_marking_sorn(self, ini_marking_in):
        suoyou_sm = set()
        this_marking_safeornot = -1
        chushi_marking = copy.deepcopy(ini_marking_in)
        chushi_marking_tuple = copy.deepcopy(self.decompose_marking_to_tuple(chushi_marking))
        if chushi_marking_tuple in self.correct_end_marking_set:
            return (1, [])
        xianzaide_marking = copy.deepcopy(chushi_marking)
        route_total_trans = []
        final_route_total_trans = []
        suoyou_sm.add(chushi_marking_tuple)
        stack = []
        stack.append([xianzaide_marking, []])
        while len(stack) > 0:
            current_stack = stack.pop()
            current_marking = copy.deepcopy(current_stack[0])
            current_total_trans = copy.deepcopy(current_stack[1])
            enabled_transitions = self.get_enabled_transitions(current_marking)
            for zhixing_t in enabled_transitions:
                next_marking = self.exe_one_trans(current_marking, zhixing_t[0], zhixing_t[1])
                next_marking_tuple = self.decompose_marking_to_tuple(next_marking)
                if next_marking_tuple in self.correct_end_marking_set:
                    this_marking_safeornot = 1
                    final_route_total_trans = copy.deepcopy(current_total_trans)
                    final_route_total_trans.append(zhixing_t)
                    return (this_marking_safeornot, final_route_total_trans)
                elif next_marking_tuple not in suoyou_sm:
                    suoyou_sm.add(next_marking_tuple)
                    next_total_trans = copy.deepcopy(current_total_trans)
                    next_total_trans.append(zhixing_t)
                    stack.append([next_marking, next_total_trans])
            if len(stack) == 0:
                this_marking_safeornot = 0
        if this_marking_safeornot == 0:
            return (0, [])
        else:
            raise ValueError('这个是找到了还是没找到')
    '\n    add_lujing_safe_marking_in_dict 函数\n    功能:\n        已知这个marking 是 safe marking了，然后添加所有的路径上的marking 都到字典中，值为1\n\n    input:\n        ini_marking_in: 输入的marking\n        frtt: final_route_total_trans\n        jilu_suoyoude_marking_safeornot: 所有marking 的字典，值为1\n\n\n    output:\n        无，但是增添了字典\n\n    '

    def add_lujing_safe_marking_in_dict(self, ini_marking_in, frtt, jilu_suoyoude_marking_safeornot):
        no_1_marking = copy.deepcopy(ini_marking_in)
        no_1_marking_tuple = self.decompose_marking_to_tuple(no_1_marking)
        no_2_marking = self.change_unreal_link_marking(ini_marking_in)
        no_2_marking_tuple = self.decompose_marking_to_tuple(no_2_marking)
        jilu_suoyoude_marking_safeornot[no_1_marking_tuple] = 1
        jilu_suoyoude_marking_safeornot[no_2_marking_tuple] = 1
        xiayige_marking = copy.deepcopy(ini_marking_in)
        for zhixing_t in frtt:
            tp_next_makring = self.exe_one_trans(xiayige_marking, zhixing_t[0], zhixing_t[1])
            xiayige_marking = copy.deepcopy(tp_next_makring)
            xiayige_marking_tuple = self.decompose_marking_to_tuple(xiayige_marking)
            jilu_suoyoude_marking_safeornot[xiayige_marking_tuple] = 1
            xiayige_marking_change_link = self.change_unreal_link_marking(xiayige_marking)
            xiayige_marking_change_link_tuple = self.decompose_marking_to_tuple(xiayige_marking_change_link)
            jilu_suoyoude_marking_safeornot[xiayige_marking_change_link_tuple] = 1

    def record_1000_rob_comp_mk(self, ccrm_print=0):
        """
            计算在控制策略下，从初始标识开始的所有可达标识
            :param initial_marking: 初始标识 M0，格式为 list
            :return: 包含 (可达标识列表, 触发次数, 缓存写入次数, 新增标识次数) 的元组
            """
        jilu_suoyoude_marking_safeornot = ValueCountingDict(counted_value=1)
        start_ttime = time.time()
        initial_marking = copy.deepcopy(self.app_start_marking_with_buffer)
        reachable_tuple_set = set()
        reachable_markings_list = []
        waitlist_queue = deque()
        rmba_result_cache = dict()
        transition_fire_count = 0
        cache_write_count = 0
        new_marking_count = 0
        waitlist_queue.append(initial_marking)
        while waitlist_queue:
            current_marking = waitlist_queue.pop()
            current_marking_tuple = self.decompose_marking_to_tuple(current_marking)
            if current_marking_tuple in reachable_tuple_set:
                continue
            reachable_tuple_set.add(current_marking_tuple)
            new_marking_count += 1
            xiayige_marking_list = self.find_next_marking_list(current_marking)
            for temp_next_marking in xiayige_marking_list:
                next_marking = copy.deepcopy(temp_next_marking)
                next_marking_tuple = self.decompose_marking_to_tuple(next_marking)
                transition_fire_count += 1
                if next_marking_tuple in reachable_tuple_set:
                    continue
                if next_marking_tuple in rmba_result_cache:
                    rmba_value = rmba_result_cache[next_marking_tuple]
                else:
                    rmba_value = self.robust_nbba_pandaun(next_marking, jilu_suoyoude_marking_safeornot)
                    rmba_result_cache[next_marking_tuple] = rmba_value
                    cache_write_count += 1
                    if len(jilu_suoyoude_marking_safeornot) >= self.Cunchu_Max_MK_Num:
                        if jilu_suoyoude_marking_safeornot.counted_value_num >= self.Cunchu_Max_MK_Num:
                            total_execution_ttime = time.time() - start_ttime
                            if ccrm_print == 1:
                                print()
                                print('已达到鲁棒可完成 marking 的存储上限，提前返回！')
                                print(f'【可达marking数: {new_marking_count:10d}')
                                print(f'【触发变迁数:     {transition_fire_count:10d}')
                                print(f'【NBBA判断数:    {cache_write_count:10d}')
                                print(f'【寻找 marking 的总时间为:      {total_execution_ttime:.4f} s')
                                print()
                                print(f'【字典存储的 marking 总数:         {len(jilu_suoyoude_marking_safeornot)}')
                            self._d028_return_line = 1583
                            return (reachable_markings_list, transition_fire_count, cache_write_count, new_marking_count, total_execution_ttime, jilu_suoyoude_marking_safeornot)
                if rmba_value == 1:
                    waitlist_queue.append(next_marking)
        end_ttime = time.time()
        total_execution_ttime = end_ttime - start_ttime
        if ccrm_print == 1:
            print()
            print('都寻找完啦！')
            print(f'【可达marking数: {new_marking_count:10d}')
            print(f'【触发变迁数:     {transition_fire_count:10d}')
            print(f'【NBBA判断数:    {cache_write_count:10d}')
            print(f'【寻找所有 marking 的总时间为:      {total_execution_ttime:.4f} s')
            print()
            print(f'【字典存储的 marking 总数:         {len(jilu_suoyoude_marking_safeornot)}')
        self._d028_return_line = 1614
        return (reachable_markings_list, transition_fire_count, cache_write_count, new_marking_count, total_execution_ttime, jilu_suoyoude_marking_safeornot)
