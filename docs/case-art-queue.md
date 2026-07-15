# Case Art Queue — illustrated cases for LinkedIn

A working list of cases worth illustrating, posting to LinkedIn, and featuring on their
Tortwell case pages. Chosen for one quality above all: **the facts make a picture.** Each
post teaches the case in one image plus a few sentences.

**Workflow** (proven on Palsgraf, 2026-07-15):
1. Generate the image (any size; wide ~16:9 works best — it gets center-cropped).
2. Hand it to Claude with the case URL → resized to 1200×627 (LinkedIn featured size),
   optimized, named for the case, added to `frontend/lib/caseArt.ts` + `public/case-art/`.
3. It becomes the page's social card AND an on-page illustration with the
   "AI-generated illustration of the facts" caption automatically.
4. Post to LinkedIn with the case URL; run it through linkedin.com/post-inspector if the
   URL was ever shared before (their cache is sticky).

**Image guidance:** period-accurate setting, one readable dramatic moment, no text in the
image except small factual annotations (the Palsgraf "about 25–30 feet" label worked
beautifully — a measurable fact IS the legal point in several of these).

---

## Done

- [x] **Palsgraf v. Long Island Railroad Co.** — tortwell.com/cases/248-ny-339
  Platform explosion, falling scale, the 25–30 feet annotation. *Hook: how far does a
  wrongdoer's duty travel? The most famous proximate-cause case in American law.*

## Queue — Torts

- [ ] **Vincent v. Lake Erie Transportation Co.** — tortwell.com/cases/109-minn-456
  Scene: 1905 — a steamship deliberately lashed tight to a wooden dock in a violent Duluth
  storm, waves smashing the dock to pieces beneath it. *Hook: keeping your ship tied to my
  dock in the storm was LEGAL — and you still owe me for the dock. Private necessity,
  incomplete privilege.*

- [ ] **Ploof v. Putnam** — tortwell.com/cases/81-vt-471
  Scene: 1904, Lake Champlain — a dock keeper unties a family's small sloop during a
  tempest; parents and children visible aboard as the boat is cast into the storm. *Hook:
  the flip side of Vincent — cast off a boat in a storm and YOU pay for what the storm
  does to it.*

- [ ] **Summers v. Tice** — tortwell.com/cases/199-p2d-1
  Scene: 1948 California quail hunt — two hunters firing simultaneously toward the viewer,
  two shot-clouds converging, a single pellet highlighted mid-flight. *Hook: two shooters,
  one pellet, no way to tell whose. So the law makes BOTH prove innocence — alternative
  liability.*

- [ ] **United States v. Carroll Towing Co.** — tortwell.com/cases/159-f2d-169
  Scene: WWII New York Harbor, 1944 — a barge adrift and sinking among crowded wartime
  shipping, its bargee conspicuously absent; maybe a chalkboard-style "B < P × L"
  annotation. *Hook: the day Judge Learned Hand turned negligence into algebra.*

- [ ] **The T.J. Hooper** — tortwell.com/cases/60-f2d-737
  Scene: 1932 — two tugs towing coal barges into a wall of Atlantic storm, and in the
  wheelhouse an empty bracket where a radio receiver should be. *Hook: everyone in the
  industry skipped radios. They were all negligent anyway — custom is not the standard
  of care.*

- [ ] **Wagner v. International Railway Co.** — tortwell.com/cases/133-ne-437
  Scene: night, 1919 — a man crawling out onto a railroad trestle over a gorge, searching
  by lantern light for his cousin thrown from the train. *Hook: "Danger invites rescue.
  The cry of distress is the summons to relief." — Cardozo. Rescuers are always
  foreseeable.*

- [ ] **Garratt v. Dailey** — tortwell.com/cases/46-wash-2d-197
  Scene: a 1955 backyard, a five-year-old boy mid-motion pulling a lawn chair away just
  as an elderly woman begins to sit. *Hook: a five-year-old can commit battery — intent
  means knowing what's substantially certain to happen, not meaning harm.*

- [ ] **Fisher v. Carrousel Motor Hotel** — tortwell.com/cases/424-sw2d-627
  Scene: a 1960s Houston buffet line — a hotel employee snatching a plate from the hands
  of a Black scientist at a professional luncheon. *Hook: battery without a bruise — the
  plate counts as the person. Dignity is what the tort protects.* (Handle with care: this
  is a civil-rights story; keep the dignity of the plaintiff at the center.)

- [ ] **Bierczynski v. Rogers** — tortwell.com/cases/239-a2d-218
  Scene: 1965 Delaware — two cars drag-racing abreast down a two-lane road, one swerving
  toward an oncoming car; the OTHER racer highlighted, untouched, far from the impact.
  *Hook: his car never touched anyone — liable anyway. Racing is concerted action.*

- [ ] **Rowland v. Christian** — tortwell.com/cases/443-p2d-561
  Scene: a 1960s San Francisco apartment bathroom — a cracked porcelain faucet handle
  coming apart in a guest's hand. *Hook: the case that made "trespasser, licensee, or
  invitee?" the wrong question in California — just be reasonable.*

## Queue — Civil Procedure

- [ ] **Pennoyer v. Neff** — tortwell.com/cases/95-us-714
  Scene: 1870s Oregon frontier — a sheriff's auction of forest land, a newspaper legal
  notice nailed to a post that no one is reading, the absent owner far away. *Hook:
  personal jurisdiction begins here — you can't take a man's land with a lawsuit he never
  heard about.*

- [ ] **International Shoe Co. v. Washington** — tortwell.com/cases/326-us-310
  Scene: 1940s — a dozen shoe salesmen fanning out across a map of Washington State,
  sample cases in hand, one shoe pinned to the map like a flag. *Hook: "minimum contacts"
  — the sentence every 1L memorizes. Presence means what you DO in a state.*

- [ ] **World-Wide Volkswagen Corp. v. Woodson** — tortwell.com/cases/444-us-286
  Scene: 1977 — a rear-ended Audi burning on I-44 in Oklahoma; ghosted in the distance,
  the small New York dealership that sold it a year earlier. *Hook: your product ending
  up in a state isn't enough — jurisdiction follows YOUR conduct, not your customer's
  road trip.*

- [ ] **Erie Railroad Co. v. Tompkins** — tortwell.com/cases/304-us-64
  Scene: a dark Pennsylvania night, 1934 — a man walking a footpath beside the tracks as
  a passing freight's open door swings toward him. *Hook: the accident that ended a
  century of "federal general common law." Every Erie doctrine question starts with this
  swinging door.*

- [ ] **Mullane v. Central Hanover Bank & Trust Co.** — tortwell.com/cases/339-us-306
  Scene: 1950 — a tiny legal notice buried in a dense newspaper page under a magnifying
  glass, beneficiaries' faces reflected in the glass. *Hook: notice must be "reasonably
  calculated" to actually reach people — publication in a paper nobody reads isn't
  process, it's theater.*

## Queue — Criminal Law

- [ ] **The Queen v. Dudley and Stephens** — tortwell.com/cases/14-qbd-273
  Scene: 1884, South Atlantic — a tiny open lifeboat on an empty ocean, four gaunt
  sailors, a turtle shell and empty tins in the bilge; storm clouds. Depict the boat and
  the desperation, not the act. *Hook: 24 days adrift. Necessity is not a defense to
  murder — the case every law student reads first.*

- [ ] **Pinkerton v. United States** — tortwell.com/cases/328-us-640
  Scene: split panel — one brother running moonshine whiskey by night; the other in a
  prison cell, and the crime's paperwork stacking up on HIS side of the bars. *Hook: he
  was in prison when the crimes happened — convicted anyway. Conspiracy makes your
  partner's crimes yours.*

- [ ] **People v. Beardsley** — tortwell.com/cases/113-nw-1128
  Scene: 1907 Michigan — a man turning away from a doorway while a woman lies unconscious
  in the room behind him. Somber, restrained. *Hook: morally monstrous, legally untouchable
  — the common law imposes no duty to rescue. The case that makes every 1L angry.*

---

**Batch idea for later:** once ~5 exist, a "Torts, illustrated" carousel post linking the
set; the images also slot into the outlines' key-cases sections if we ever want art there.
