import xgboost as xgb
from features import FEATURES


def xgb_params(device):
    return dict(objective="count:poisson", max_depth=3, learning_rate=0.03, subsample=0.8,
                colsample_bytree=0.8, min_child_weight=20, reg_lambda=5.0, tree_method="hist",
                device=device, max_delta_step=0.7)


def train_xgb_pair(train, device=None, rounds=None):
    """Two Poisson boosters (home goals, away goals). Early-stops on the last training season."""
    import shutil
    device = device or ("cuda" if shutil.which("nvidia-smi") else "cpu")   # GPU boosting in Colab
    last = train.season.max()
    tr, va = train[train.season < last], train[train.season == last]
    models, best = {}, {}
    for tgt in ["hg", "ag"]:
        dtr = xgb.DMatrix(tr[FEATURES], label=tr[tgt])
        dva = xgb.DMatrix(va[FEATURES], label=va[tgt])
        if rounds is None:
            b = xgb.train(xgb_params(device), dtr, 3000, evals=[(dva, "va")],
                          early_stopping_rounds=150, verbose_eval=False)
            best[tgt] = b.best_iteration + 1
        else:
            best[tgt] = rounds[tgt]
        dall = xgb.DMatrix(train[FEATURES], label=train[tgt])
        models[tgt] = xgb.train(xgb_params(device), dall, best[tgt])
    return models, best
