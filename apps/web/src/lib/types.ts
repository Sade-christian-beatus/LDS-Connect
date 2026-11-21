// Alias lisibles des types générés depuis l'OpenAPI de l'API (pnpm gen:api).
import type { components } from "./api-schema";

type S = components["schemas"];

export type Season = S["SeasonOut"];
export type PublicTeam = S["PublicTeam"];
export type PublicTeamDetail = S["PublicTeamDetail"];
export type TeamRef = S["TeamRef"];
export type Match = S["MatchOut"];
export type PoolStandings = S["PoolStandings"];
export type StandingRow = S["StandingRow"];
export type Sheet = S["SheetOut"];
export type TeamSheet = S["TeamSheetOut"];
export type Candidate = S["CandidateOut"];
export type LineupEntryIn = S["LineupEntryIn"];
export type EventIn = S["EventIn"];
export type SheetEvent = S["EventOut"];
export type DelegateMatch = S["DelegateMatch"];
export type User = S["UserOut"];
export type TokenOut = S["TokenOut"];
export type PublicKeys = S["PublicKeysOut"];
export type EventType = S["EventIn"]["type"];
