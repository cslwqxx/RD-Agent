import pickle
import site
import traceback
from pathlib import Path
from typing import Dict, Optional

from rdagent.components.coder.CoSTEER.task import CoSTEERTask
from rdagent.core.experiment import Experiment, FBWorkspace
from rdagent.core.utils import cache_with_pickle
from rdagent.oai.llm_utils import md5_hash
from rdagent.utils.env import DockerEnv, DSDockerConf

# TODO: Complete the implementation of the class DataLoaderTask and class DataLoaderFBWorkspace

class ModelTask(CoSTEERTask):
    def __init__(
        self,
        name: str,
        description: str,
        architecture: str,
        *args,
        hyperparameters: Dict[str, str],
        formulation: str = None,
        variables: Dict[str, str] = None,
        model_type: Optional[str] = None,
        **kwargs,
    ) -> None:
        self.formulation: str = formulation
        self.architecture: str = architecture
        self.variables: str = variables
        self.hyperparameters: str = hyperparameters
        self.model_type: str = (
            model_type  # Tabular for tabular model, TimesSeries for time series model, Graph for graph model, XGBoost for XGBoost model 
            # TODO: More Models Supported
        )
        super().__init__(name=name, description=description, *args, **kwargs)

    def get_task_information(self):
        task_desc = f"""name: {self.name}
description: {self.description}
"""
        task_desc += f"formulation: {self.formulation}\n" if self.formulation else ""
        task_desc += f"architecture: {self.architecture}\n"
        task_desc += f"variables: {self.variables}\n" if self.variables else ""
        task_desc += f"hyperparameters: {self.hyperparameters}\n"
        task_desc += f"model_type: {self.model_type}\n"
        return task_desc

    @staticmethod
    def from_dict(dict):
        return ModelTask(**dict)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"

class ModelFBWorkspace(FBWorkspace):
    def execute(self):
        super().execute()
        try:
            de = DockerEnv(DSDockerConf())
            de.prepare()
            np.save(os.path.join(self.workspace_path, "train_X.npy"), train_X)  
            np.save(os.path.join(self.workspace_path, "train_y.npy"), train_y)  
            np.save(os.path.join(self.workspace_path, "val_X.npy"), val_X)  
            np.save(os.path.join(self.workspace_path, "val_y.npy"), val_y)  
            np.save(os.path.join(self.workspace_path, "test_X.npy"), test_X)  
            # TODO: generate dataset automatically

            dump_code = (Path(__file__).parent / "model_execute_template.txt").read_text()

            log, results = de.dump_python_code_run_and_get_results(
                code=dump_code,
                dump_file_names=["execution_feedback_str.pkl", "val_pred.pkl", "test_pred.pkl"],  
                local_path=str(self.workspace_path),
                env={},
                code_dump_file_py_name="model_test",
            )
            if results is None:
                raise RuntimeError(f"Error in running the model code: {log}")
            [execution_feedback_str, execution_model_output] = results

        except Exception as e:
            execution_feedback_str = f"Execution error: {e}\nTraceback: {traceback.format_exc()}"
            val_pred_array = None  
            test_pred_array = None 

        if len(execution_feedback_str) > 2000:
            execution_feedback_str = (
                execution_feedback_str[:1000] + "....hidden long error message...." + execution_feedback_str[-1000:]
            )
        return execution_feedback_str, val_pred_array, test_pred_array 
    