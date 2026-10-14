"""Verified project curation. Daily collection never rewrites this copy."""

FEATURED = (
    ("panel", "PlexonPanel", "OPERATIONS"),
    ("tools", "PlexonTools", "PROGRESSION"),
    ("quests", "PlexonQuests", "PLAYER JOURNEYS"),
    ("chats", "PlexonChats", "COMMUNICATION"),
    ("companion", "AI-Desktop-Companion", "DESKTOP & 3D"),
    ("core", "PlexonCore", "SHARED RUNTIME"),
)

GROUPS = (
    ("Operations", ("PlexonPanel", "PlexonPanel-Dashboard", "PlexonUtility")),
    ("Progression", ("PlexonTools", "PlexonQuests", "PlexonRanks", "PlexonSkills")),
    ("Rewards", ("PlexonKeys", "Plexon-DailyRewards", "PlexonCrates")),
    ("Community & jobs", ("PlexonChats", "PlexonShops", "PlexonJobs")),
    ("World & inventory", ("PlexonHomes", "PlexonTravel", "PlexonBackpacks", "PlexonSpawners", "PlexonBlacksmith")),
    ("Claim policy", ("PlexonGPFlags", "PlexonGriefPreventionAddon")),
)
STATUS = {"PlexonCrates": "retired", "PlexonGriefPreventionAddon": "deprecated"}
SHORT = {"PlexonPanel-Dashboard": "Panel Dashboard", "Plexon-DailyRewards": "DailyRewards",
         "PlexonGriefPreventionAddon": "GriefPreventionAddon", "AI-Desktop-Companion": "Desktop Companion"}
WEB_PROJECTS = frozenset(("AI-Desktop-Companion", "ConanGrayBot-Page", "Neural-Core-Dashboard",
                          "PlexonPanel-Dashboard", "Trabalho-III-Eng.-Prompt", "Triangle-Area"))
SERVER_PROJECTS = frozenset(("GhostBlocks", "DropsEditor", "Rankup-1.2Fixer", "PlexonCore",
                            *(name for _, names in GROUPS for name in names
                              if name != "PlexonPanel-Dashboard")))
SHELF_PROJECTS = tuple(name for _, name, _ in FEATURED) + (
    "PlexonSkills", "PlexonJobs", "PlexonHomes", "PlexonTravel", "PlexonGPFlags", "PlexonSpawners")


def short_name(name):
    return SHORT.get(name, name.removeprefix("Plexon"))

