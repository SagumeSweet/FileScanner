import json
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from queue import Queue
from typing import Union, Callable, Optional

from .Logger import IScannerLogger
from .Processer import IProcesser, BaseProcessResult, DefaultProcesser


class FolderScanner:
    def __init__(self, root_path: Union[str, Path], executor: ThreadPoolExecutor, logger: IScannerLogger, processer: IProcesser = DefaultProcesser()) -> None:
        self._root_path: Path = Path(root_path)
        self._executor: ThreadPoolExecutor = executor
        self._futures: Queue[Future] = Queue()
        self._results_queue: Queue[BaseProcessResult] = Queue()
        self._results: Optional[BaseProcessResult] = None
        self._processer: IProcesser = processer
        self._logger: IScannerLogger = logger

    @property
    def root_path(self) -> Path:
        """获取根路径"""
        return self._root_path

    @root_path.setter
    def root_path(self, path: Union[str, Path]) -> None:
        """设置根路径"""
        self._root_path = Path(path)

    @property
    def result(self) -> BaseProcessResult:
        """获取结果"""
        results: BaseProcessResult = self._processer.empty_process_result
        if not self._results_queue.empty() and self._results is None:
            while not self._results_queue.empty():
                results += self._results_queue.get()
            self._results = results
        elif not self._results_queue.empty() and self._results is not None:
            raise RuntimeError("线程可能未正确结束，结果可能不完整")
        elif self._results_queue.empty() and self._results is not None:
            results = self._results
        else:
            self._logger.warning("扫描结果为空")
            results = self._processer.empty_process_result
        return results

    def _submit_thread(self, func: Callable, *args, **kwargs) -> None:
        """提交线程任务"""
        self._logger.info("Submitting thread %s", func.__name__)
        future: Future = self._executor.submit(func, *args, **kwargs)
        self._futures.put(future)

        def done_callback(fut):
            self._futures.task_done()

        future.add_done_callback(done_callback)

    def scan(self) -> BaseProcessResult:
        """启动扫描并返回所有文件路径的列表"""
        self._submit_thread(self._scan_folder, self._root_path)
        self._futures.join()
        if self._results is not None:
            self._results = None
        return self.result

    def _scan_folder(self, folder_path: Path) -> None:
        """递归扫描单个文件夹，返回该文件夹及子文件夹下的所有文件路径"""
        for entry in folder_path.iterdir():
            self._logger.debug(f"Scanning: {entry}")
            if entry.is_dir():
                self._submit_thread(self._scan_folder, entry)
            elif entry.is_file():
                self._results_queue.put(self._processer.process(entry))

    def convert_to_json_file(self) -> None:
        """将处理结果转换为 JSON 文件"""

        class PathEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, Path):
                    return str(obj.resolve())
                return super().default(obj)

        file_path = Path(f"{self._processer.__class__.__name__}_result.json")
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(self.result.data, f, ensure_ascii=False, indent=4, cls=PathEncoder)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
