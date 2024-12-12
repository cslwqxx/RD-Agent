from abc import abstractmethod
from dataclasses import dataclass
from typing import List

from rdagent.components.coder.CoSTEER.evolvable_subjects import EvolvingItem
from rdagent.core.conf import RD_AGENT_SETTINGS
from rdagent.core.evaluation import Evaluator, Feedback
from rdagent.core.evolving_framework import QueriedKnowledge
from rdagent.core.experiment import Workspace
from rdagent.core.scenario import Task
from rdagent.core.utils import multiprocessing_wrapper
from rdagent.log import rdagent_logger as logger


# TODO:
# 1. It seems logically sound, but we currently lack a scenario to apply it.
# 2. If it proves to be useful, relocate it to a more general location.
#
# class FBWorkspaceExeFeedback(Feedback):
#     """
#     It pairs with FBWorkspace in the abstract level.
#     """
#     # ws: FBWorkspace   # potential
#     stdout: str


@dataclass
class CoSTEERSingleFeedback(Feedback):
    # TODO: (xiao)
    # it should be more general class for FBWorkspaceExeFeedback
    # A better name of it may be NormalFeedback
    # TODO: It should be a general feeddback for CoSTEERR
    """
    The feedback for the data loader evaluation.
    It is design align the phases of the implemented code
    - Execution -> Return Value -> Code -> Final Decision
    """
    execution: str
    # execution_feedback
    return_checking: str | None  # inlucding every check in the testing (constraints about the generated value)
    # value_feedback, shape_feedback, value_generated_flag
    code: str
    final_decision: bool

    def __str__(self) -> str:
        return f"""------------------Execution------------------
{self.execution}
------------------Return Checking------------------
{self.return_checking if self.return_checking is not None else 'No return checking'}
------------------Code------------------
{self.code}
------------------Final Decision------------------
This implementation is {'SUCCESS' if self.final_decision else 'FAIL'}.
"""

class CoSTEERSingleFeedbackDeprecated(CoSTEERSingleFeedback):
    """This class is a base class for all code generator feedback to single implementation"""

    def __init__(
        self,
        execution_feedback: str = None,
        shape_feedback: str = None,
        code_feedback: str = None,
        value_feedback: str = None,
        final_decision: bool = None,
        final_feedback: str = None,
        value_generated_flag: bool = None,
        final_decision_based_on_gt: bool = None,
    ) -> None:
        self.execution_feedback = execution_feedback
        self.code_feedback = code_feedback
        self.value_feedback = value_feedback
        self.final_decision = final_decision
        self.final_feedback = final_feedback
        self.value_generated_flag = value_generated_flag
        self.final_decision_based_on_gt = final_decision_based_on_gt

        # TODO:
        # Not general enough. So we should not put them in the general costeer feedback
        # Instead, we should create subclass for it.
        self.shape_feedback = shape_feedback  # Not general enough. So 

    # TODO: @property

    def __str__(self) -> str:
        return f"""------------------Execution Feedback------------------
{self.execution_feedback if self.execution_feedback is not None else 'No execution feedback'}
------------------Shape Feedback------------------
{self.shape_feedback if self.shape_feedback is not None else 'No shape feedback'}
------------------Code Feedback------------------
{self.code_feedback if self.code_feedback is not None else 'No code feedback'}
------------------Value Feedback------------------
{self.value_feedback if self.value_feedback is not None else 'No value feedback'}
------------------Final Feedback------------------
{self.final_feedback if self.final_feedback is not None else 'No final feedback'}
------------------Final Decision------------------
This implementation is {'SUCCESS' if self.final_decision else 'FAIL'}.
"""


class CoSTEERMultiFeedback(
    Feedback,
    List[CoSTEERSingleFeedback],
):
    """Feedback contains a list, each element is the corresponding feedback for each factor implementation."""


class CoSTEEREvaluator(Evaluator):
    # TODO:
    # I think we should have unified interface for all evaluates, for examples.
    # So we should adjust the interface of other factors
    @abstractmethod
    def evaluate(
        self,
        target_task: Task,
        implementation: Workspace,
        gt_implementation: Workspace,
        **kwargs,
    ) -> CoSTEERSingleFeedback:
        raise NotImplementedError("Please implement the `evaluator` method")


class CoSTEERMultiEvaluator(Evaluator):
    def __init__(self, single_evaluator: CoSTEEREvaluator, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.single_evaluator = single_evaluator

    def evaluate(
        self,
        evo: EvolvingItem,
        queried_knowledge: QueriedKnowledge = None,
        **kwargs,
    ) -> CoSTEERMultiFeedback:
        multi_implementation_feedback = multiprocessing_wrapper(
            [
                (
                    self.single_evaluator.evaluate,
                    (
                        evo.sub_tasks[index],
                        evo.sub_workspace_list[index],
                        evo.sub_gt_implementations[index] if evo.sub_gt_implementations is not None else None,
                        queried_knowledge,
                    ),
                )
                for index in range(len(evo.sub_tasks))
            ],
            n=RD_AGENT_SETTINGS.multi_proc_n,
        )

        final_decision = [
            None if single_feedback is None else single_feedback.final_decision
            for single_feedback in multi_implementation_feedback
        ]
        logger.info(f"Final decisions: {final_decision} True count: {final_decision.count(True)}")

        for index in range(len(evo.sub_tasks)):
            if final_decision[index]:
                evo.sub_tasks[index].factor_implementation = True

        return multi_implementation_feedback
