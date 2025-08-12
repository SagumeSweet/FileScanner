import json
from concurrent.futures import ThreadPoolExecutor, Future
from pathlib import Path
from queue import Queue
from typing import Union, Callable

from .Logger import IScannerLogger
from .Processer import Processer, IProcesser, BaseProcessResult


class FolderScanner:
    def __init__(self, root_path: Union[str, Path], logger: IScannerLogger, max_workers: int = 10, processer: IProcesser = Processer(), ) -> None:
        self._root_path: Path = Path(root_path)
        self._executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: Queue[Future] = Queue()
        self._results_queue: Queue[BaseProcessResult] = Queue()
        self._processer: IProcesser = processer
        self._logger: IScannerLogger = logger

    def __enter__(self) -> "FolderScanner":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._executor.shutdown(wait=True)

    @property
    def result(self) -> BaseProcessResult:
        """获取结果"""
        results: BaseProcessResult = self._processer.empty_process_result
        while not self._results_queue.empty():
            results += self._results_queue.get()
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
        file_path = Path(f"{self._processer.__class__.__name__}_result.json")
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(self.result.data, f, ensure_ascii=False, indent=4)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True)
