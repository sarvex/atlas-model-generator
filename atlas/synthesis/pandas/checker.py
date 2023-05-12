import logging
from typing import Any, Callable, Collection

import numpy as np
import pandas as pd

pd_groupby = pd.core.groupby.GroupBy
pd_series_groupby = pd.core.groupby.SeriesGroupBy
pd_df_groupby = pd.core.groupby.DataFrameGroupBy


class Checker:
    @staticmethod
    def check(v1: Any, v2: Any) -> bool:
        return Checker.get_checker(v1)(v1, v2)

    @staticmethod
    def get_checker(v1: Any) -> Callable[[Any, Any], bool]:
        if isinstance(v1, pd.DataFrame):
            return Checker.check_dataframe
        if isinstance(v1, pd.Series):
            return Checker.check_series
        if isinstance(v1, pd_groupby):
            return Checker.check_groupby
        if isinstance(v1, np.ndarray):
            return Checker.check_ndarray
        if isinstance(v1, str):
            return Checker.check_default
        if isinstance(v1, Collection):
            return Checker.check_collection

        return Checker.check_default

    @staticmethod
    def check_dataframe(v1: pd.DataFrame, v2: Any) -> bool:
        if not isinstance(v2, pd.DataFrame):
            return False

        try:
            pd.testing.assert_frame_equal(v1, v2, check_names=False)
            return True
        except (AssertionError, TypeError, ValueError):
            return False
        except Exception as e:
            logging.exception(e)
            return False

    @staticmethod
    def check_series(v1: pd.Series, v2: Any) -> bool:
        if not isinstance(v2, pd.Series):
            return False

        try:
            pd.testing.assert_series_equal(v1, v2, check_names=False)
            return True
        except (AssertionError, TypeError, ValueError):
            return False
        except Exception as e:
            logging.exception(e)
            return False

    @staticmethod
    def check_groupby(v1: pd_groupby, v2: Any) -> bool:
        if not isinstance(v2, pd_groupby):
            return False

        if isinstance(v1, pd_df_groupby) and not isinstance(v2, pd_df_groupby):
            return False

        if isinstance(v1, pd_series_groupby) and not isinstance(v2, pd_series_groupby):
            return False

        try:
            if list(v1.groups.keys()) != list(v2.groups.keys()):
                return False

            if isinstance(v1, pd_df_groupby):
                return Checker.check_dataframe(v1.obj, v2.obj)

            if isinstance(v1, pd_series_groupby):
                return Checker.check_series(v1.obj, v2.obj)

        except (AssertionError, TypeError, ValueError, NameError):
            return False
        except Exception as e:
            logging.exception(e)
            return False

    @staticmethod
    def check_index(v1: pd.Index, v2: Any) -> bool:
        if not isinstance(v2, pd.Index):
            return False

        try:
            pd.testing.assert_index_equal(v1, v2)
            return True
        except (AssertionError, TypeError, ValueError):
            return False
        except Exception as e:
            logging.exception(e)
            return False

    @staticmethod
    def check_ndarray(v1: np.ndarray, v2: Any) -> bool:
        if not isinstance(v2, np.ndarray):
            return False

        try:
            return np.array_equal(v1, v2)
        except Exception as e:
            logging.exception(e)
            return False

    @staticmethod
    def check_collection(v1: Collection, v2: Any) -> bool:
        if (not isinstance(v2, Collection)) or isinstance(v2, str):
            return False

        if len(v1) != len(v2):
            return False

        try:
            for i, j in zip(v1, v2):
                if not Checker.check(i, j):
                    return False

        except Exception as e:
            logging.exception(e)
            return False

        return True

    @staticmethod
    def check_default(v1: Any, v2: Any) -> bool:
        try:
            return v1 == v2
        except (AssertionError, TypeError, ValueError, NameError):
            return False
        except Exception as e:
            logging.exception(e)
            return False


