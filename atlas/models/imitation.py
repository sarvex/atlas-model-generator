import datetime
import os
import pickle
import shutil
import tempfile
from abc import ABC, abstractmethod
from typing import Collection, Dict, Optional, Any

import tqdm
from atlas.models import GeneratorModel, AtlasModel
from atlas.models.utils import save_model, restore_model
from atlas.operators import OpInfo, OpResolvable, find_known_operators, resolve_operator
from atlas.tracing import GeneratorTrace, OpTrace
from atlas.utils.ioutils import IndexedFileWriter, IndexedFileReader


class TraceImitationModel(GeneratorModel, ABC):
    @abstractmethod
    def train(self, traces: Collection[GeneratorTrace], *args, **kwargs):
        pass


class IndependentOperatorsModel(TraceImitationModel, OpResolvable, ABC):
    def __init__(self):
        work_dir = tempfile.mkdtemp(prefix=f"generator-model-{datetime.datetime.today():%d-%m-%Y-%H-%M-%S}")
        self.work_dir = work_dir
        self.model_map: Dict[OpInfo, AtlasModel] = {}
        self.model_paths: Dict[OpInfo, str] = {}

        self.model_definitions = find_known_operators(self)

    def train(self,
              train_traces: Collection[GeneratorTrace],
              val_traces: Collection[GeneratorTrace] = None,
              **kwargs):

        #  First, go over all the traces and create separate data-sets for each operator
        train_datasets: Dict[OpInfo, Collection[OpTrace]] = self.create_operator_datasets(train_traces)
        val_datasets: Dict[OpInfo, Collection[OpTrace]] = {}
        if val_traces is not None:
            val_datasets: Dict[OpInfo, Collection[OpTrace]] = self.create_operator_datasets(val_traces, mode='validation')

        for op_info, dataset in train_datasets.items():
            model: AtlasModel = self.get_op_model(op_info)
            if model is None:
                continue

            print(f"[+] Training model for {op_info}")
            model_dir = f"{self.work_dir}/models/{op_info.sid}"
            self.model_map[op_info] = model
            self.model_paths[op_info] = model_dir

            model.train(dataset, val_datasets.get(op_info, None), **kwargs)
            save_model(model, model_dir, no_zip=True)

    def infer(self, domain: Any, context: Any = None, op_info: OpInfo = None, **kwargs):
        if op_info not in self.model_map:
            return None

        return self.model_map[op_info].infer(domain, context, op_info, **kwargs)

    def create_operator_datasets(self, traces: Collection[GeneratorTrace],
                                 mode: str = 'training') -> Dict[OpInfo, Collection[OpTrace]]:
        file_maps: Dict[str, IndexedFileWriter] = {}
        path_maps: Dict[str, str] = {}
        for trace in tqdm.tqdm(traces):
            for op in trace.op_traces:
                op_info = op.op_info
                if op_info not in file_maps:
                    path = f"{self.work_dir}/data/{op_info.sid}"
                    os.makedirs(path, exist_ok=True)
                    file_maps[op_info] = IndexedFileWriter(f"{path}/{mode}_op_data.pkl")
                    path_maps[op_info] = f"{path}/{mode}_op_data.pkl"

                file_maps[op_info].append(op)

        for v in file_maps.values():
            v.close()

        return {k: IndexedFileReader(v) for k, v in path_maps.items()}

    def get_op_model(self, op_info: OpInfo) -> Optional[AtlasModel]:
        try:
            return resolve_operator(self.model_definitions, op_info)(self, op_info.sid)
        except ValueError:
            return None

    def serialize(self, path: str):
        with open(f"{path}/model_list.pkl", "wb") as f:
            pickle.dump({k: os.path.relpath(v, self.work_dir) for k, v in self.model_paths.items()}, f)

        if path != self.work_dir:
            shutil.rmtree(f"{path}/models", ignore_errors=True)
            shutil.copytree(f"{self.work_dir}/models", f"{path}/models")

    def deserialize(self, path: str):
        with open(f"{path}/model_list.pkl", "rb") as f:
            self.model_paths = {k: f"{path}/{v}" for k, v in pickle.load(f).items()}

        self.load_models()

    def load_models(self):
        for op_info, model_dir in self.model_paths.items():
            if op_info not in self.model_map:
                self.model_map[op_info] = restore_model(model_dir)

    def __getstate__(self):
        state = self.__dict__.copy()
        state.pop('model_map')
        state.pop('model_paths')
        state.pop('model_definitions')

        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.model_map: Dict[OpInfo, AtlasModel] = {}
        self.model_paths: Dict[OpInfo, str] = {}

        self.model_definitions = find_known_operators(self)
