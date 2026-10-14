"""Editorial cover. One travelling signal connects conceptual layers."""

from .draw import display_text, text, rect, path, dot, shell


def cover(theme, mobile=False):
    w, h = (500, 440) if mobile else (1000, 338)
    body = text(32, 38, "ZPKDXGAMES / DEVELOPER", 15 if mobile else 13, "violet", 650,
                extra='letter-spacing="2"')
    body += display_text(28, 128 if mobile else 143, "Tonim.", 86 if mobile else 104)
    body += display_text(32, 175 if mobile else 198, "Engineering systems.", 27 if mobile else 29)
    body += display_text(32, 212 if mobile else 237, "Crafting experiences.", 27 if mobile else 29, "violet")
    chips = [("SERVER SYSTEMS", "violet"), ("WEB INTERFACES", "cyan"), ("AUTOMATION", "text-muted")]
    for i, (label, color) in enumerate(chips):
        x = 32+i*(145 if mobile else 169)
        y = 239 if mobile else 268
        bw = 136 if mobile else 156
        body += rect(x, y, bw, 30, "surface", 6, True)
        body += text(x+bw/2, y+20, label, 11 if mobile else 12, color, 650, "middle")
    if mobile:
        body += path("M32 293H468")
        body += text(32, 326, "LOGIC", 15, "text-muted", 550)
        body += text(204, 326, "INTERACTION", 15, "text-muted", 550)
        body += text(404, 326, "TOOLS", 15, "text-muted", 550)
        body += path("M53 358H446", "violet", 2)
        body += path("M53 358H446", "cyan", 3, 'class="signal"')
        for x, color in ((53, "violet"), (249, "cyan"), (446, "violet")):
            body += rect(x-17, 341, 34, 34, "surface", 7, True)
            body += dot(x, 358, color, 5)
        body += text(32, 413, "THOUGHTFUL SYSTEMS. EXPRESSIVE WORLDS.", 13, "text-muted", 550)
    else:
        body += path("M604 40V298")
        body += text(644, 65, "FROM LOGIC TO EXPERIENCE", 12, "text-muted", 550, extra='letter-spacing="1.5"')
        for i, (label, color) in enumerate((('SYSTEM', 'violet'), ('INTERFACE', 'cyan'), ('TOOL', 'violet'))):
            x, y = 656+i*25, 91+i*54
            body += rect(x, y, 218, 65, "surface", 9, True)
            body += text(x+18, y+26, label, 12, color, 650, extra='letter-spacing="1.3"')
            for j, length in enumerate((78, 47, 25)):
                body += path(f"M{x+19+j*53} {y+43}h{min(length,40)}", color, 2)
        d = "M922 103V126H969V180H921V222H946V261H810"
        body += path(d, "violet", 1.5)
        body += path(d, "cyan", 2.5, 'class="signal"')
        body += dot(922, 103, "violet", 4)+dot(810, 261, "cyan", 4)
        body += text(644, 299, "CONCEPTUAL SYSTEM STUDY", 11, "text-muted", 500, extra='letter-spacing="1.4"')
    return shell(theme, w, h, "Tonim / ZpkDxGames — Engineering systems. Crafting experiences.",
                 "Minecraft server systems, web interfaces and automation. Conceptual system artwork, not product screenshots or live telemetry.", body)
