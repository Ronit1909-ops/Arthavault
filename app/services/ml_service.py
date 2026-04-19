"""
app/services/ml_service.py – ML model loader and inference service.

Models loaded at startup (once):
  - category_classifier.joblib   → XGBoost category predictor
  - tfidf_vectorizer.joblib      → TF-IDF vectorizer for merchant names
  - feature_info.joblib          → Feature metadata (label encoder / category list)
  - expense_forecaster.joblib    → Prophet spending forecaster
  - anomaly_detector.joblib      → Isolation Forest anomaly detector
  - anomaly_scaler.joblib        → StandardScaler for anomaly feature normalisation
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional


logger = logging.getLogger(__name__)

# ── Model directory (sibling of app/ → app/models/) ──────────────────────────
_MODELS_DIR = Path(__file__).parent.parent / "models"

_MODEL_FILES = {
    "classifier":  "category_classifier.joblib",
    "vectorizer":  "tfidf_vectorizer.joblib",
    "feature_info": "feature_info.joblib",
    "forecaster":  "expense_forecaster.joblib",
    "detector":    "anomaly_detector.joblib",
    "scaler":      "anomaly_scaler.joblib",
}


def _load_joblib(name: str, filename: str) -> Any | None:
    """Try to load a joblib file; return None and log a warning on failure."""
    path = _MODELS_DIR / filename
    if not path.exists():
        logger.warning("⚠  Model file not found: %s (skipping %s)", path, name)
        return None
    try:
        import joblib
        model = joblib.load(path)
        logger.info("✓  Loaded %-18s  ← %s", name, path.name)
        return model
    except Exception as exc:
        logger.error("✗  Failed to load %s (%s): %s", name, filename, exc)
        return None


# ─────────────────────────────────────────────────────────────────────────────
class MLService:
    """
    Singleton-style ML service.  Instantiate once at startup and share via
    FastAPI dependency injection (see routers/ml.py).
    """

    def __init__(self) -> None:
        logger.info("Loading ML models from %s …", _MODELS_DIR)

        self.classifier   = _load_joblib("classifier",   _MODEL_FILES["classifier"])
        self.vectorizer   = _load_joblib("vectorizer",   _MODEL_FILES["vectorizer"])
        self.feature_info = _load_joblib("feature_info", _MODEL_FILES["feature_info"])
        self.forecaster   = _load_joblib("forecaster",   _MODEL_FILES["forecaster"])
        self.detector     = _load_joblib("detector",     _MODEL_FILES["detector"])
        self.scaler       = _load_joblib("scaler",       _MODEL_FILES["scaler"])

        # Derive the ordered category labels from feature_info
        self._categories: list[str] = self._resolve_categories()

        loaded = sum(
            1 for m in [
                self.classifier, self.vectorizer, self.feature_info,
                self.forecaster, self.detector,   self.scaler,
            ]
            if m is not None
        )
        logger.info("ML models ready: %d / %d loaded.", loaded, len(_MODEL_FILES))

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _resolve_categories(self) -> list[str]:
        """Extract the class-label list from feature_info."""
        fi = self.feature_info
        if fi is None:
            return []
        # feature_info may be a plain dict …
        if isinstance(fi, dict):
            cats: list | None = fi.get("categories") or fi.get("classes")
            return list(cats) if cats else []
        # … or a fitted LabelEncoder / similar with .classes_
        classes = getattr(fi, "classes_", None)
        if classes is not None:
            return list(classes)
        return []

    def _build_features(
        self,
        merchants: list[str],
        amounts: list[float],
        hours: list[int],
        days_of_week: list[int],
    ):
        """
        Combine TF-IDF merchant features + numerical features using
        scipy.sparse.hstack (exact same pipeline as training).
        Returns a sparse matrix ready for predict / predict_proba.
        """
        import numpy as np
        from scipy.sparse import hstack, csr_matrix

        tfidf_matrix = self.vectorizer.transform(merchants)

        numerical = np.array(
            list(zip(amounts, hours, days_of_week)),
            dtype=np.float32,
        )
        numerical_sparse = csr_matrix(numerical)

        return hstack([tfidf_matrix, numerical_sparse])

    @property
    def categorization_ready(self) -> bool:
        return self.classifier is not None and self.vectorizer is not None

    @property
    def forecasting_ready(self) -> bool:
        return self.forecaster is not None

    @property
    def anomaly_ready(self) -> bool:
        return self.detector is not None and self.scaler is not None

    # ── Public API ────────────────────────────────────────────────────────────

    def categorize_transaction(
        self,
        merchant: str,
        amount: float,
        hour: int,
        day_of_week: int,
    ) -> dict:
        """
        Predict the spending category for a single transaction.

        Parameters
        ----------
        merchant    : Merchant / description string (raw text).
        amount      : Transaction amount in INR.
        hour        : Hour of day (0–23).
        day_of_week : Day of week (0=Monday … 6=Sunday).

        Returns
        -------
        {
            "category": "Food",
            "confidence": 0.92,
            "top_3_predictions": [
                {"category": "Food",          "probability": 0.92},
                {"category": "Shopping",      "probability": 0.05},
                {"category": "Entertainment", "probability": 0.03},
            ],
        }
        """
        if not self.categorization_ready:
            logger.warning("Categorization models unavailable — returning default.")
            return {
                "category": "Uncategorized",
                "confidence": 0.0,
                "top_3_predictions": [],
            }

        try:
            features = self._build_features(
                [merchant], [amount], [hour], [day_of_week]
            )
            pred_idx = int(self.classifier.predict(features)[0])
            proba    = self.classifier.predict_proba(features)[0]

            # Map index → label
            categories = self._categories or list(range(len(proba)))
            pred_label = str(categories[pred_idx]) if self._categories else str(pred_idx)

            top3_idx = list(reversed(sorted(range(len(proba)), key=lambda i: proba[i])))[:3]
            top3 = [
                {
                    "category":    str(categories[i]) if self._categories else str(i),
                    "probability": round(float(proba[i]), 4),
                }
                for i in top3_idx
            ]

            return {
                "category":          pred_label,
                "confidence":        round(float(proba[pred_idx]), 4),
                "top_3_predictions": top3,
            }

        except Exception as exc:
            logger.error("categorize_transaction error: %s", exc)
            return {
                "category": "Uncategorized",
                "confidence": 0.0,
                "top_3_predictions": [],
            }

    def categorize_batch(self, transactions: list[dict]) -> list[dict]:
        """
        Batch-categorise multiple transactions efficiently (single vectorizer call).

        Parameters
        ----------
        transactions : List of dicts with keys:
            merchant (str), amount (float), hour (int, optional),
            day_of_week (int, optional).

        Returns
        -------
        List of result dicts parallel to the input, each containing:
            category (str), confidence (float), top_3_predictions (list).
        """
        if not transactions:
            return []

        if not self.categorization_ready:
            logger.warning("Categorization models unavailable — returning defaults.")
            return [
                {"category": "Uncategorized", "confidence": 0.0, "top_3_predictions": []}
                for _ in transactions
            ]

        try:
            merchants    = [t.get("merchant", "") for t in transactions]
            amounts      = [float(t.get("amount", 0.0)) for t in transactions]
            hours        = [int(t.get("hour", 12)) for t in transactions]
            days_of_week = [int(t.get("day_of_week", 0)) for t in transactions]

            features  = self._build_features(merchants, amounts, hours, days_of_week)
            pred_idxs = self.classifier.predict(features)
            probas    = self.classifier.predict_proba(features)

            categories = self._categories or list(range(probas.shape[1]))
            results: list[dict] = []

            for pred_idx, proba in zip(pred_idxs, probas):
                pred_idx   = int(pred_idx)
                pred_label = str(categories[pred_idx]) if self._categories else str(pred_idx)
                top3_idx = list(reversed(sorted(range(len(proba)), key=lambda i: proba[i])))[:3]
                top3 = [
                    {
                        "category":    str(categories[i]) if self._categories else str(i),
                        "probability": round(float(proba[i]), 4),
                    }
                    for i in top3_idx
                ]
                results.append({
                    "category":          pred_label,
                    "confidence":        round(float(proba[pred_idx]), 4),
                    "top_3_predictions": top3,
                })

            return results

        except Exception as exc:
            logger.error("categorize_batch error: %s", exc)
            return [
                {"category": "Uncategorized", "confidence": 0.0, "top_3_predictions": []}
                for _ in transactions
            ]

    async def forecast_spending(
        self,
        user_id: str,
        days: int = 30,
        db=None,
    ) -> dict:
        """
        Fetch user transaction history from MongoDB and generate a spending forecast.

        Strategy (in order of preference):
          1. Prophet (if installed) — best accuracy for long histories
          2. Exponential smoothing with weekly seasonality — reliable statistical fallback
          3. Weighted moving average — last resort for very sparse data
        """
        import pandas as pd

        # ── Fetch historical debits ────────────────────────────────────────────
        col  = db["transactions"]
        docs = await col.find(
            {"user_id": user_id, "type": "debit"},
            {"date": 1, "amount": 1, "_id": 0},
        ).to_list(length=None)

        if not docs:
            logger.info("No transaction history for user %s; returning empty forecast.", user_id)
            return {"forecast": [], "total_predicted": 0.0, "confidence_interval": "80%"}

        # ── Aggregate daily spend ──────────────────────────────────────────────
        df = pd.DataFrame(docs)
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        df["ds"]     = pd.to_datetime(df["date"]).dt.normalize()
        daily = (
            df.groupby("ds")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"amount": "y"})
        )
        daily = daily.sort_values("ds").reset_index(drop=True)

        if daily.empty:
            return {"forecast": [], "total_predicted": 0.0, "confidence_interval": "80%"}

        # ── Try Prophet first ──────────────────────────────────────────────────
        if len(daily) >= 2:
            try:
                from prophet import Prophet  # type: ignore
                import logging as _logging
                _logging.getLogger("prophet").setLevel(_logging.ERROR)
                _logging.getLogger("cmdstanpy").setLevel(_logging.ERROR)

                m = Prophet(
                    yearly_seasonality=False,
                    weekly_seasonality=True,
                    daily_seasonality=False,
                    interval_width=0.80,
                    changepoint_prior_scale=0.15,
                )
                m.fit(daily)
                future       = m.make_future_dataframe(periods=days)
                forecast_df  = m.predict(future)
                last_hist    = daily["ds"].max()
                fut          = forecast_df[forecast_df["ds"] > last_hist].head(days)

                result_rows = [
                    {
                        "date":            row["ds"].strftime("%Y-%m-%d"),
                        "predicted_spend": round(max(float(row["yhat"]),       0.0), 2),
                        "lower_bound":     round(max(float(row["yhat_lower"]), 0.0), 2),
                        "upper_bound":     round(max(float(row["yhat_upper"]), 0.0), 2),
                    }
                    for _, row in fut.iterrows()
                ]
                total = round(sum(r["predicted_spend"] for r in result_rows), 2)
                logger.info("Prophet forecast OK for user %s (%d days).", user_id, days)
                return {"forecast": result_rows, "total_predicted": total, "confidence_interval": "80%"}

            except Exception as exc:
                logger.warning("Prophet unavailable for user %s (%s) — using stat fallback.", user_id, exc)

        # ── Statistical fallback: exponential smoothing + weekly seasonality ───
        return self._stat_forecast(daily, days)

    # ── Statistical forecast (no Prophet dependency) ──────────────────────────
    def _stat_forecast(self, daily, days: int) -> dict:
        """
        Exponential smoothing with day-of-week seasonal factors.

        Steps
        -----
        1. Fill sparse calendar gaps (missing days → 0 spend).
        2. Compute exponentially-weighted moving average (α = 0.35).
        3. Derive day-of-week multiplicative seasonal factors from the last
           8 weeks of data (gives realistic Mon-Sun rhythm).
        4. Blend the smoothed baseline with seasonal factors.
        5. Estimate 80 % confidence bounds from historical daily variance.
        """
        import numpy as np
        from datetime import date, timedelta
        import pandas as pd

        try:
            # 1. Full daily calendar (fill gaps with 0)
            full_idx = pd.date_range(daily["ds"].min(), daily["ds"].max(), freq="D")
            s = daily.set_index("ds")["y"].reindex(full_idx, fill_value=0.0)

            if len(s) == 0:
                return {"forecast": [], "total_predicted": 0.0, "confidence_interval": "50%"}

            # 2. Exponential smoothing baseline
            alpha = 0.35
            smoothed = s.ewm(alpha=alpha, adjust=False).mean()
            baseline = float(smoothed.iloc[-1])          # last smoothed value as anchor
            baseline = max(baseline, 0.0)

            # Also compute a 7-day and 30-day simple average for blend
            avg_7d  = float(s.iloc[-7:].mean())  if len(s) >= 7  else float(s.mean())
            avg_30d = float(s.iloc[-30:].mean()) if len(s) >= 30 else float(s.mean())
            # Weighted blend: 50% EWMA anchor, 30% 7-day avg, 20% 30-day avg
            blended_base = 0.50 * baseline + 0.30 * avg_7d + 0.20 * avg_30d
            blended_base = max(blended_base, 0.0)

            # 3. Day-of-week seasonal factors (last 8 weeks max)
            recent = s.iloc[-min(len(s), 56):]          # up to 56 days
            dow_means = recent.groupby(recent.index.dayofweek).mean()
            overall_mean = float(dow_means.mean()) if float(dow_means.mean()) > 0 else 1.0
            seasonal = (dow_means / overall_mean).to_dict()  # {0:Mon, 6:Sun}
            # Fill any missing DOW with 1.0
            for d in range(7):
                seasonal.setdefault(d, 1.0)

            # 4. Historical std for confidence bands
            std = float(s[s > 0].std()) if (s > 0).any() else blended_base * 0.4
            if std == 0 or np.isnan(std):
                std = blended_base * 0.4
            # 80% CI ≈ ±1.28 σ
            ci_half = 1.28 * std

            # 5. Build forecast rows
            start   = date.today()
            result_rows = []
            for i in range(1, days + 1):
                fdate   = start + timedelta(days=i)
                dow     = fdate.weekday()               # 0=Mon … 6=Sun
                sf      = seasonal.get(dow, 1.0)        # seasonal factor
                sf      = max(sf, 0.0)                  # guard against negatives
                pred    = blended_base * sf
                pred    = max(round(pred, 2), 0.0)
                lo      = max(round(pred - ci_half, 2), 0.0)
                hi      = round(pred + ci_half, 2)
                result_rows.append({
                    "date":            fdate.strftime("%Y-%m-%d"),
                    "predicted_spend": pred,
                    "lower_bound":     lo,
                    "upper_bound":     hi,
                })

            total = round(sum(r["predicted_spend"] for r in result_rows), 2)
            logger.info(
                "Stat forecast for user (blended_base=%.2f, std=%.2f, days=%d).",
                blended_base, std, days,
            )
            return {"forecast": result_rows, "total_predicted": total, "confidence_interval": "80%"}

        except Exception as exc:
            logger.error("_stat_forecast error: %s", exc, exc_info=True)
            return {"forecast": [], "total_predicted": 0.0, "confidence_interval": "80%"}

    async def detect_anomalies(
        self,
        user_id: str,
        days: int = 30,
        db=None,
    ) -> list[dict]:
        """
        Fetch recent transactions and flag anomalies using Isolation Forest.

        Parameters
        ----------
        user_id : MongoDB user _id string.
        days    : Look-back window (days from today).
        db      : AsyncIOMotorDatabase instance.

        Returns
        -------
        List of transaction dicts with anomaly metadata:
        [
            {
                "transaction_id": "...",
                "merchant":       "MAKEMYTRIP",
                "amount":         15000,
                "date":           "2024-06-22",
                "is_anomaly":     true,
                "anomaly_score":  -0.45,
                "explanation":    "Amount is 8x your average travel spend",
            },
            ...
        ]
        Only returns transactions flagged as anomalies (is_anomaly=True).
        """
        if not self.anomaly_ready:
            logger.warning("Anomaly detection models unavailable — returning empty list.")
            return []

        try:
            import pandas as pd

            since = datetime.now(timezone.utc) - timedelta(days=days)
            col   = db["transactions"]
            docs  = await col.find(
                {"user_id": user_id, "date": {"$gte": since}, "type": "debit"},
            ).to_list(length=None)

            if not docs:
                return []

            df = pd.DataFrame(docs)
            df["hour"]         = pd.to_datetime(df["date"]).dt.hour
            df["day_of_week"]  = pd.to_datetime(df["date"]).dt.dayofweek

            # ── Build feature matrix ───────────────────────────────────────
            import numpy as np
            feature_cols = ["amount", "hour", "day_of_week"]
            X_raw = df[feature_cols].fillna(0).values.astype(np.float32)
            X_scaled = self.scaler.transform(X_raw)

            # ── Predict anomalies ──────────────────────────────────────────
            scores = self.detector.decision_function(X_scaled)   # lower = more anomalous
            labels = self.detector.predict(X_scaled)             # -1 = anomaly, 1 = normal

            # Per-merchant average for explanation
            avg_by_merchant = (
                df.groupby("merchant")["amount"]
                .mean()
                .to_dict()
            )

            anomalies: list[dict] = []
            for idx, (label, score) in enumerate(zip(labels, scores)):
                if label != -1:
                    continue
                row      = docs[idx]
                merchant = row.get("merchant", "Unknown")
                amount   = float(row.get("amount", 0))
                avg      = avg_by_merchant.get(merchant, amount)

                if avg > 0 and amount > 0:
                    ratio = amount / avg
                    explanation = (
                        f"Amount is {ratio:.1f}x your average {merchant} spend"
                        if ratio >= 1.5
                        else f"Unusual transaction pattern for {merchant}"
                    )
                else:
                    explanation = "Unusual transaction detected by anomaly model"

                anomalies.append({
                    "transaction_id": str(row.get("_id", "")),
                    "merchant":       merchant,
                    "amount":         amount,
                    "date":           row["date"].strftime("%Y-%m-%d") if hasattr(row["date"], "strftime") else str(row["date"]),
                    "is_anomaly":     True,
                    "anomaly_score":  round(float(score), 4),
                    "explanation":    explanation,
                })

            logger.info(
                "Anomaly detection for user %s: %d / %d flagged (window=%d days)",
                user_id, len(anomalies), len(docs), days,
            )
            return anomalies

        except Exception as exc:
            logger.error("detect_anomalies error for user %s: %s", user_id, exc)
            return []

    # ── Health snapshot ───────────────────────────────────────────────────────

    def health(self) -> dict:
        """Return a status snapshot of all models (for /ml/health)."""
        return {
            "models_loaded": all([
                self.classifier, self.vectorizer, self.feature_info,
                self.forecaster, self.detector, self.scaler,
            ]),
            "models": {
                "category_classifier": self.classifier is not None,
                "tfidf_vectorizer":    self.vectorizer  is not None,
                "feature_info":        self.feature_info is not None,
                "expense_forecaster":  self.forecaster  is not None,
                "anomaly_detector":    self.detector    is not None,
                "anomaly_scaler":      self.scaler      is not None,
            },
        }


# ── Module-level singleton (imported by main.py and routers) ─────────────────
ml_service = MLService()
