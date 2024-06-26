import json
import os
from typing import List
from dataclasses import dataclass, field

import settings
from futuur.futuur_api import FutuurAPI
from manifold.manifold_api import ManifoldAPI


@dataclass
class MatchingOutcome:
    title: str
    futuur_probability: float
    manifold_probability: float


@dataclass
class MatchingMarket:
    futuur_title: str
    futuur_id: int
    manifold_id: str
    total_probability: float = 1
    outcomes: List[MatchingOutcome] = field(default_factory=list)


class Analizer:
    def __init__(self):
        """
        Initializes the Analizer that will determine if there are or not arbitrage oportunities
        """
        self.manifold_api = ManifoldAPI()
        self.futuur_api = FutuurAPI(
            settings.FUTUUR_PUBLIC_KEY, settings.FUTUUR_PRIVATE_KEY
        )
        self.matching_markets = self.retrieve_matching_markets_outcomes()

    def retrieve_matching_markets_outcomes(self, currency="OOM"):
        matching_markets = self.load_markets_from_json()

        for market in matching_markets:
            futuur_market = self.futuur_api.get_market(market.futuur_id)
            market.futuur_title = futuur_market.get("title")
            mani_market = self.manifold_api.get_market_by_id(market.manifold_id)

            if mani_market.get("outcomeType") == "BINARY":
                mani_awnsers = [
                    {"text": "yes", "probability": mani_market.get("probability")},
                    {"text": "no", "probability": 1 - mani_market.get("probability")},
                ]
            else:
                mani_awnsers = mani_market.get("answers")
            futuur_outcomes = futuur_market.get("outcomes")
            total_probability = 0
            for m in mani_awnsers:

                matches = False
                for o in futuur_outcomes:
                    if m.get("text").lower().strip() == o.get("title").lower().strip():
                        probability_mani = m["probability"]
                        probability_futuur = o["price"][currency]
                        smaller_probability = min(probability_mani, probability_futuur)
                        total_probability += smaller_probability
                        matches = True
                        market.outcomes.append(
                            MatchingOutcome(
                                o.get("title"), probability_futuur, probability_mani
                            )
                        )
                if not matches:
                    total_probability += m["probability"]

            market.total_probability = total_probability

        return matching_markets

    def load_markets_from_json(self, path="markets.json"):
        markets = []
        abs_path = os.path.abspath(path)
        try:
            with open(abs_path, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            return [
                MatchingMarket(
                    futuur_title="",
                    futuur_id=133793,
                    manifold_id="Z9uy9T4q4rAfq4sGzPA0",
                )
            ]

        for obj in data:
            markets.append(
                MatchingMarket(
                    futuur_title="",
                    futuur_id=obj.get("futuur"),
                    manifold_id=obj.get("mani"),
                )
            )

        return markets

    def display_arbitrage(self):
        for market in self.matching_markets:
            print("\n\nMarket: " + market.futuur_title)
            if market.total_probability < 1:
                for outcome in market.outcomes:
                    where_bet = (
                        "Manifold"
                        if outcome.manifold_probability < outcome.futuur_probability
                        else "Futuur"
                    )
                    smaller_probability = min(
                        outcome.manifold_probability, outcome.futuur_probability
                    )
                    optimal_bet_amount = smaller_probability / market.total_probability

                    print(
                        "Bet on",
                        where_bet,
                        outcome.title,
                        "with amount:",
                        optimal_bet_amount,
                    )
