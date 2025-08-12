from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable


class BaseProcessResult(ABC):
    def __init__(self, data):
        self._data = data

    @property
    def data(self):
        """获取处理后的结果"""
        return self._data


    def _calculation_error_str(self, other):
        """获取计算错误的字符串表示"""
        return f"Unsupported operand type(s): '{self.__class__.__name__}' and '{type(other).__name__}'"

    @abstractmethod
    def _add(self, other: "BaseProcessResult") -> "BaseProcessResult":
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def _iadd(self, other: "BaseProcessResult") -> None:
        raise NotImplementedError("Subclasses must implement this method")

    def __str__(self):
        return str(self._data)

    def __add__(self, other) -> "BaseProcessResult":
        """重载加法运算符，返回一个新的 ProcessResult"""
        if type(other) == type(self):
            return self._add(other)
        raise TypeError(self._calculation_error_str(other))

    def __iadd__(self, other) -> "BaseProcessResult":
        """重载加法赋值运算符"""
        if type(other) == type(self):
            self._iadd(other)
            return self
        raise TypeError(self._calculation_error_str(other))

class ProcessResult(BaseProcessResult):
    def __init__(self, data):
        super().__init__(data)

    def _add(self, other: "ProcessResult") -> "ProcessResult":
        """重载加法运算符，返回一个新的 ProcessResult"""
        return ProcessResult(self.data + other.data)

    def _iadd(self, other: "ProcessResult") -> None:
        """重载加法赋值运算符"""
        self._data += other.data


class IProcesser(ABC):
    @abstractmethod
    def process(self, path: Path) -> BaseProcessResult:
        """处理数据，返回处理结果"""
        raise NotImplementedError("Subclasses must implement this method")

    @property
    @abstractmethod
    def empty_process_result(self) -> BaseProcessResult:
        """处理数据，返回处理结果"""
        raise NotImplementedError("Subclasses must implement this method")


class Processer(IProcesser):
    def __init__(self, fuc: Callable[[Path], BaseProcessResult]=lambda x: ProcessResult([x])):
        self._fuc: Callable = fuc

    def process(self, path: Path) -> BaseProcessResult:
        """处理数据，默认返回原数据"""
        return self._fuc(path)

    @property
    def empty_process_result(self) -> BaseProcessResult:
        return ProcessResult([])
