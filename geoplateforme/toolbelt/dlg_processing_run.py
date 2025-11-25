# standard
from functools import partial
from pathlib import Path
from typing import Any, Optional, Tuple

# PyQGIS
from qgis.core import (
    QgsApplication,
    QgsProcessingAlgRunnerTask,
    QgsProcessingContext,
    QgsProcessingFeedback,
)
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox, QWidget

# project
from geoplateforme.toolbelt.text_edit_feedback import QTextEditProcessingFeedBack


class ProcessingRunDialog(QDialog):
    def __init__(
        self,
        params: dict[str, Any],
        alg_name: str,
        title: str,
        parent: Optional[QWidget] = None,
    ):
        """QDialog to run a processing and wait for finish

        :param params: processing parameters
        :type params: dict[str, Any]
        :param alg_name: algorithm name
        :type alg_name: str
        :param title: display title
        :type title: str
        :param parent: dialog parent, defaults to None
        :type parent: QWidget, optional
        """

        super().__init__(parent)

        uic.loadUi(Path(__file__).parent / f"{Path(__file__).stem}.ui", self)

        self.title = title
        self.lbl_title.setText(title)

        self._feedback = QTextEditProcessingFeedBack(self.te_logs_processing)
        self._task = None

        self._results: dict[str, Any] = {}
        self._successful = False

        self.btn_box.setVisible(False)
        self.btn_box.rejected.connect(self.cancel_processing)

        self._processing_in_progress = True

        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(True)
        self.te_logs_processing.setVisible(False)
        self._run_alg(
            alg_name=alg_name, params=params, executed_callback=self.callback_processing
        )

    def enable_cancel(self, enable: bool) -> None:
        """Enable display of cancel button

        :param enable: _description_
        :type enable: bool
        """
        self.btn_box.setVisible(enable)

    def cancel_processing(self) -> None:
        """Cancel processing with user confirmation"""
        reply = QMessageBox.question(
            self,
            self.tr("Cancel processing"),
            self.tr("Do you want to cancel processing {} ?".format(self.title)),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self._task:
                self._task.cancel()
            # Need to use super(), because we override reject() to avoid close during processing
            super().reject()

    def processing_results(self) -> Tuple[bool, dict[str, Any]]:
        """Return processing resust

        :return: tuple of success, result : True if processing is sucessfull, false otherwise and dict of processing result
        :rtype: Tuple[bool, dict[str, Any]]
        """
        return self._successful, self._results

    def get_feedback(self) -> QgsProcessingFeedback:
        """Return processing feedback

        :return: _description_
        :rtype: QgsProcessingFeedback
        """
        return self._feedback

    def callback_processing(
        self, context, successful: bool, results: dict[str, Any]
    ) -> None:
        """Function call after processing run

        :param context: processing context
        :type context: _type_
        :param successful: True if processing is sucessfull, False otherwise
        :type successful: bool
        :param results: processing results
        :type results: dict[str, Any]
        """
        self._processing_in_progress = False
        self.setEnabled(True)
        self.progress_bar.setVisible(False)

        self._results = results
        self._successful = successful

        if not successful:
            self.progress_bar.setValue(0)
            self.te_logs_processing.setVisible(True)
        else:
            self.accept()

    def _run_alg(self, alg_name: str, params: dict, executed_callback) -> None:
        """
        Executes a QGIS processing algorithm with the provided parameters.

        :param alg_name: The name or identifier of the QGIS algorithm to execute.
        :type alg_name: str
        :param params: A dictionary containing the required parameters for the algorithm.
        :type params: dict
        :param executed_callback: Callback function that will be called after the algorithm execution.
        :type executed_callback: callable
        """
        context = QgsProcessingContext()
        alg = QgsApplication.processingRegistry().algorithmById(alg_name)
        self.setWindowTitle(alg.displayName())
        res, error = alg.checkParameterValues(params, context)
        self.te_logs_processing.clear()
        self._feedback = QTextEditProcessingFeedBack(self.te_logs_processing)
        if res:
            self._task = QgsProcessingAlgRunnerTask(
                alg, params, context, self._feedback
            )
            self._task.executed.connect(partial(executed_callback, context))
            QgsApplication.taskManager().addTask(self._task)
        else:
            self._processing_in_progress = False
            self.setEnabled(True)
            self.progress_bar.setVisible(False)
            self._feedback.reportError(self.tr("Can't run {0}".format(alg.name())))
            self._feedback.reportError(
                self.tr("Invalid parameters : {0}.".format(error))
            )
            self.te_logs_processing.setVisible(True)

    def reject(self) -> None:
        """Override reject to check for processing run"""
        if not self._processing_in_progress:
            super().reject()
