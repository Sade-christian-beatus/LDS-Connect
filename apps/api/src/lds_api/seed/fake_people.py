"""Génération de personnes fictives (aucune donnée réelle).

Les noms sont tirés au hasard dans des listes de prénoms et noms courants ; les numéros
CNIB et téléphones sont manifestement factices (préfixes « X » et « +226 00 »).
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta

from lds_api.models.enums import Foot, Position, StaffFunction

FIRST_NAMES = [
    "Abdoul", "Adama", "Alassane", "Amadou", "Arouna", "Aziz", "Bakary", "Boukary", "Brice",
    "Cédric", "Cheick", "Christian", "Daouda", "Dieudonné", "Drissa", "Edgar", "Elisée",
    "Fabrice", "Fousseni", "Hamado", "Harouna", "Hervé", "Ibrahim", "Idrissa", "Issa",
    "Issouf", "Jean", "Josué", "Karim", "Lamine", "Lassina", "Mahamadi", "Moussa", "Nestor",
    "Noufou", "Ousmane", "Patrice", "Rasmané", "Salif", "Sami", "Seydou", "Siaka", "Souleymane",
    "Tahirou", "Wendkouni", "Yacouba", "Yves", "Zakaria",
]  # fmt: skip

LAST_NAMES = [
    "Bamogo", "Barro", "Bationo", "Belem", "Compaoré", "Coulibaly", "Dabiré", "Dao", "Diallo",
    "Drabo", "Guiro", "Hien", "Ilboudo", "Kaboré", "Kambou", "Kiemtoré", "Kinda", "Konaté",
    "Koné", "Nana", "Nikiéma", "Ouattara", "Ouédraogo", "Palm", "Sanou", "Sanogo", "Sawadogo",
    "Simporé", "Somé", "Sorgho", "Tapsoba", "Tiendrébéogo", "Traoré", "Yaméogo", "Zan",
    "Zongo", "Zoungrana",
]  # fmt: skip

# Répartition par poste pour un effectif de 30
POSITIONS = (
    [Position.GOALKEEPER] * 3
    + [Position.DEFENDER] * 10
    + [Position.MIDFIELDER] * 9
    + [Position.FORWARD] * 8
)

STAFF_FUNCTIONS = [
    StaffFunction.HEAD_COACH,
    StaffFunction.ASSISTANT_COACH,
    StaffFunction.GOALKEEPER_COACH,
    StaffFunction.FITNESS_COACH,
    StaffFunction.DOCTOR,
    StaffFunction.PHYSIO,
    StaffFunction.TEAM_MANAGER,
]


@dataclass
class FakePerson:
    first_name: str
    last_name: str
    birth_date: date
    cnib: str
    phone: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name[0]}. {self.last_name}"


@dataclass
class FakePlayer:
    person: FakePerson
    position: Position
    foot: Foot
    shirt_number: int
    # True : réside dans la région de l'équipe ; False : autre région
    resides_in_team_region: bool
    residence_since: date


def _birth_date(rng: random.Random, reference: date, age: int) -> date:
    """Date de naissance donnant exactement `age` ans à la date de référence."""
    latest = date(reference.year - age, reference.month, reference.day)
    return latest - timedelta(days=rng.randint(0, 364))


def fake_person(rng: random.Random, reference: date, age: int) -> FakePerson:
    return FakePerson(
        first_name=rng.choice(FIRST_NAMES),
        last_name=rng.choice(LAST_NAMES),
        birth_date=_birth_date(rng, reference, age),
        cnib=f"X{rng.randint(10_000_000, 99_999_999)}",
        phone=f"+22600{rng.randint(100_000, 999_999)}",
    )


def fake_squad(rng: random.Random, reference: date, *, size: int = 30, youth: int = 8):
    """Effectif fictif : `youth` joueurs de 16 à 18 ans, environ 75 % de résidents locaux,
    dont quelques-uns arrivés depuis moins de 6 mois (pour exercer la règle des locaux)."""
    ages = [rng.randint(16, 18) for _ in range(youth)] + [
        rng.randint(19, 33) for _ in range(size - youth)
    ]
    rng.shuffle(ages)
    positions = POSITIONS[:size]
    players = []
    for i, (age, pos) in enumerate(zip(ages, positions, strict=True)):
        local = rng.random() < 0.75
        months = rng.choice([2, 4]) if rng.random() < 0.1 else rng.randint(7, 120)
        players.append(
            FakePlayer(
                person=fake_person(rng, reference, age),
                position=pos,
                foot=rng.choices([Foot.RIGHT, Foot.LEFT, Foot.BOTH], [70, 22, 8])[0],
                shirt_number=i + 1,
                resides_in_team_region=local,
                residence_since=reference - timedelta(days=months * 30),
            )
        )
    return players


def fake_staff(rng: random.Random, reference: date):
    return [(fake_person(rng, reference, rng.randint(30, 60)), f) for f in STAFF_FUNCTIONS]
