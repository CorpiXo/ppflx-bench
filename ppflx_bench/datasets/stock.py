"""
Stock market (CERN) dataset loader.

Source: Kaggle "Price Volume Data for US Stocks & ETFs"
  One ticker (CERN), 3,180 trading days after feature warm-up.
  Target: StockMove (1 = next close higher, 0 = not).
  11 features: Open, Close and OpenInt; the previous day's volume; the 20-day
  moving average and standard deviation, the two Bollinger bands and the distance
  from the mean; and the overnight-return sign, one-hot (two columns).
"""

from __future__ import annotations

from typing import List, Tuple

from torch.utils.data import DataLoader

from ppflx_bench.datasets.base import DatasetSpec, DatasetLoader
from ppflx_bench.datasets.registry import register_dataset
from ppflx_bench.datasets.creditcard import _partition_tabular


@register_dataset("stock")
class StockLoader(DatasetLoader):
    spec = DatasetSpec(
        name="stock",
        input_dim=11,
        num_classes=2,
        is_tabular=True,
        class_names=["down", "up"],
    )

    def load(self, config) -> Tuple[List[DataLoader], List[DataLoader], DataLoader]:
        from ppflx_bench.datasets.sources import load_stock_market_data, StockMarketDataset

        print("Loading Stock Market dataset…")
        X_train, X_test, y_train, y_test = load_stock_market_data()

        trainset = StockMarketDataset(X_train, y_train)
        testset = StockMarketDataset(X_test, y_test)

        return _partition_tabular(trainset, testset, config)
