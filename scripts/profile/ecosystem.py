"""All snapshot Plexon modules; grouping is editorial, not a dependency graph."""

from .draw import text, rect, path, shell
from .editorial import GROUPS, STATUS


def ecosystem_map(data, theme, mobile=False):
    w = 500 if mobile else 1000
    present = {p['name'] for p in data['projects'] if p['name'].startswith('Plexon')}
    grouped = [(label, [n for n in names if n in present]) for label, names in GROUPS]
    known = {n for _, names in GROUPS for n in names}|{'PlexonCore'}
    unknown = sorted(present-known)
    if unknown:
        grouped.append(('Additional modules', unknown))
    body = text(28, 35, 'THE PLEXON ECOSYSTEM', 16 if mobile else 14, 'violet', 650, extra='letter-spacing="1.6"')
    if mobile:
        body += text(28, 76, 'Focused modules.', 28, weight=650)
        body += text(28, 109, 'Shared foundation.', 28, weight=650)
    else:
        body += text(28, 76, 'Focused modules. Shared foundation.', 30, weight=650)
    body += text(28, 139 if mobile else 105, f"{len(present)} repositories in the snapshot · {data['as_of']}", 17 if mobile else 16, 'text-muted')
    if mobile:
        y = 163
        for i, (label, names) in enumerate(grouped):
            gh = 50+len(names)*31+sum(n in STATUS for n in names)*22
            body += rect(28, y, 444, gh, 'surface', 10, True)
            body += text(46, y+28, f"{i+1:02d} / {label}", 17, 'violet', 650)
            cy = y+59
            for n in names:
                body += text(46, cy, n, 19, weight=500, max_width=402)
                if n in STATUS:
                    body += text(46, cy+22, STATUS[n].upper()+' · historical source', 15, 'text-muted')
                    cy += 22
                cy += 31
            y += gh+14
        core_y = y+7
        h = core_y+176
    else:
        y = 130
        for row_start in range(0,len(grouped),3):
            row = grouped[row_start:row_start+3]
            gh = max(60+len(names)*26+sum(n in STATUS for n in names)*20 for _, names in row)
            for j, (label, names) in enumerate(row):
                i = row_start+j
                x = 28+j*320
                body += rect(x, y, 304, gh, 'surface', 10, True)
                body += text(x+18, y+29, f"{i+1:02d} / {label}", 15, 'violet', 650)
                cy = y+59
                for n in names:
                    body += text(x+18, cy, n, 16, weight=500, max_width=268)
                    if n in STATUS:
                        body += text(x+18, cy+19, STATUS[n].upper()+' · historical source', 12, 'text-muted')
                        cy += 20
                    cy += 26
            y += gh+20
        core_y = y+5
        h = core_y+150
    body += rect(28, core_y, w-56, 84 if mobile else 74, 'surface-2', 10, True)
    core_label = 'PlexonCore' if 'PlexonCore' in present else 'No PlexonCore in this snapshot'
    body += text(46, core_y+29, core_label, 24 if mobile else 22, 'violet', 650)
    body += text(46, core_y+57, 'Runtime · configuration · UI · storage · diagnostics', 16 if mobile else 17, 'text-muted', max_width=w-90)
    body += text(28, h-47, 'An overview, not a dependency contract.', 17 if mobile else 15, 'text-muted')
    body += text(28, h-22, 'Integration and maintenance vary by repository.', 16 if mobile else 15, 'text-muted')
    return shell(theme,w,h,'Plexon ecosystem — complete public snapshot overview',
                 f"All {len(present)} Plexon repositories as of {data['as_of']}: "+', '.join(sorted(present))+
                 '. PlexonCrates is retired; PlexonGriefPreventionAddon is deprecated. Grouping describes areas of work, not required dependencies.',body)
