"""Read-only SVG presentation for the Task 2 evidence-collection world.

No engine imports or third-party drawing packages. In Jupyter, finish a cell
with view.render(wm, t), or call view.show(wm, t). See README.md.
"""
from dataclasses import dataclass
import base64
import mimetypes
from html import escape
from pathlib import Path

__all__ = ['WorldView', 'SVGFrame']

DEFAULT_LAYOUT = {
    'library': (336, 110), 'laboratory': (636, 110),
    'foyer': (36, 370), 'hallway': (336, 370),
    'gallery': (636, 370), 'study': (936, 370),
    'garden': (36, 630), 'terrace': (336, 630),
}
LABELS = {'letter_opener': 'Letter opener', 'sample_vial': 'Sample vial'}

def label(value):
    return LABELS.get(str(value), str(value).replace('_', ' ').capitalize())

def esc(value):
    return escape(str(value), quote=True)

def image_uri(path):
    """Embed local images so SVG snapshots remain portable and offline."""
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode('ascii')

def facts_of(source):
    """Take a private copy; source can be WorkingMemory or an iterable of tuples."""
    return {tuple(f) for f in getattr(source, 'facts', source)}

@dataclass(frozen=True)
class SVGFrame:
    svg: str

    def _repr_svg_(self):
        return self.svg

    def save(self, filename):
        """Write an optional SVG snapshot (the renderer never saves automatically)."""
        path = Path(filename)
        path.write_text(self.svg, encoding='utf-8')
        return path

class WorldView:
    """Fixed floor plan with positions obtained ONLY from the requested time.

    initial_facts supplies the roster and reference layout/links, not fallback
    state. Missing current facts are shown as unknown. Layout coordinates are
    top-left positions for 230x190 room cards on a 1600x900 canvas.
    """
    def __init__(self, initial_facts, actor='sherlock', target='foyer', layout=None,
                 background=None, actor_image=None):
        assets = Path(__file__).resolve().parent / 'assets'
        default_background = assets / 'ravenwick_background.png'
        default_actor = assets / 'sherlock.png'
        # False disables an asset; None uses the bundled default if present.
        bg = default_background if background is None and default_background.exists() else background
        robot = default_actor if actor_image is None and default_actor.exists() else actor_image
        self.background = image_uri(bg) if bg else None
        self.actor_image = image_uri(robot) if robot else None
        self.initial = facts_of(initial_facts)
        self.actor = actor
        self.target = target
        self.layout = dict(DEFAULT_LAYOUT if layout is None else layout)
        self.objects = {f[1] for f in self.initial if len(f) == 3 and f[0] == 'object'}
        self.evidence = {f[1] for f in self.initial if len(f) == 3 and f[0] == 'evidence'}
        self.links = {(f[1], f[2]) for f in self.initial if len(f) == 4 and f[0] == 'passage'}

    def inspect(self, source, t):
        """Return a display model, useful for debugging; does not infer world facts."""
        if not isinstance(t, int) or isinstance(t, bool) or t < 0:
            raise ValueError('t must be a non-negative integer')
        all_facts = facts_of(source)
        current = {f for f in all_facts if f and f[-1] == t}
        rooms = {f[1] for f in current if len(f) == 3 and f[0] == 'location'}
        objects = self.objects | {f[1] for f in current if len(f) == 3 and f[0] == 'object'}
        evidence = self.evidence | {f[1] for f in current if len(f) == 3 and f[0] == 'evidence'}
        positions = {}
        for f in current:
            if len(f) == 4 and f[0] == 'at':
                positions.setdefault(f[1], set()).add(f[2])
        held = {f[1] for f in current if len(f) == 3 and f[0] == 'holding'}
        held |= {f[2] for f in current if len(f) == 4 and f[0] == 'holding' and f[1] == self.actor}
        objects |= held
        empty = ('empty', self.actor, t) in current
        links = {(f[1], f[2]) for f in current if len(f) == 4 and f[0] == 'passage'}
        warnings = []
        actor_rooms = positions.get(self.actor, set())
        if len(actor_rooms) > 1:
            warnings.append('Robot has conflicting locations.')
        if empty and held:
            warnings.append('Robot is both empty and holding an object.')
        if len(held) > 1:
            warnings.append('Robot holds multiple objects.')
        statuses = {}
        for obj in sorted(objects, key=str):
            places = positions.get(obj, set())
            if len(places) > 1 or (obj in held and places):
                statuses[obj] = 'Conflicting facts'
                warnings.append(f'{label(obj)} has conflicting facts.')
            elif obj in held:
                statuses[obj] = 'Held by robot'
            elif places:
                place = next(iter(places))
                statuses[obj] = label(place)
            else:
                statuses[obj] = 'Unknown location'
        for entity, places in positions.items():
            for room in places:
                if room not in self.layout:
                    warnings.append(f'{label(entity)}: {label(room)} is outside this map.')
                elif room not in rooms:
                    warnings.append(f'{label(room)} has no location declaration at this step.')
        unknown_rooms = rooms - self.layout.keys()
        if unknown_rooms:
            warnings.append('Unmapped rooms: ' + ', '.join(map(label, sorted(unknown_rooms, key=str))))
        return dict(time=t, facts=current, rooms=rooms, objects=objects, evidence=evidence,
                    positions=positions, held=held, empty=empty, links=links,
                    statuses=statuses, warnings=warnings)

    def render(self, source, t, title='Ravenwick Manor | The evidence courier'):
        """Return an SVGFrame; display as the last expression in a Jupyter cell."""
        s = self.inspect(source, t)
        out = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 1600 900" role="img" aria-label="Evidence world">',
               '<style>text{font-family:Arial,sans-serif;fill:#e9edf6} .muted{fill:#9caec7} .room{font-size:19px;font-weight:bold} .tiny{font-size:12px} .body{font-size:15px}</style>',
               '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#d1a85f"/></marker></defs>',
               '<rect width="1600" height="900" rx="20" fill="#101c2c"/>']
        if self.background:
            out.append(f'<image xlink:href="{self.background}" x="0" y="0" width="1600" height="900" preserveAspectRatio="xMidYMid slice"/>')
            out.append('<rect width="1600" height="900" rx="20" fill="#0c1525" fill-opacity="0.52"/>')
        def text(x,y,value,cls='body',color=None):
            fill = f' style="fill:{color}"' if color else ''
            out.append(f'<text x="{x}" y="{y}" class="{cls}"{fill}>{esc(value)}</text>')
        text(36,44,title,'room')
        text(36,72,'WORKING MEMORY / LIVE STATE', 'tiny')
        text(1050,44,f'STEP {t:02d}', 'room','#e9bd70')
        text(1050,72,f'{len(s["facts"])} facts at this step', 'tiny')
        # Fixed links are map references; current directions determine arrows.
        pairs = {tuple(sorted((a,b), key=str)) for a,b in self.links | s['links'] if a != b}
        for a,b in sorted(pairs, key=repr):
            if a not in self.layout or b not in self.layout:
                continue
            ax,ay=self.layout[a]; bx,by=self.layout[b]
            dx,dy=bx-ax,by-ay
            if abs(dx) >= abs(dy):
                sign=1 if dx>0 else -1
                x1,y1=ax+115+sign*115,ay+95
                x2,y2=bx+115-sign*115,by+95
            else:
                sign=1 if dy>0 else -1
                x1,y1=ax+115,ay+95+sign*95
                x2,y2=bx+115,by+95-sign*95
            active=(a,b) in s['links'] or (b,a) in s['links']
            attrs = 'stroke="#d1a85f"' if active else 'stroke="#48556a" stroke-dasharray="5 5"'
            if (a,b) in s['links']: attrs+=' marker-end="url(#arrow)"'
            if (b,a) in s['links']: attrs+=' marker-start="url(#arrow)"'
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke-width="3" {attrs}/>')
        actor_places=s['positions'].get(self.actor,set())
        robot_room=next(iter(actor_places)) if len(actor_places)==1 else None
        for room,(x,y) in self.layout.items():
            known=room in s['rooms']; robot_here=room==robot_room
            fill='#183d42' if room in ('garden','terrace') else '#213149'
            stroke='#e9bd70' if robot_here else '#806947'
            out.append(f'<rect x="{x}" y="{y}" width="230" height="190" rx="15" fill="{fill if known else "#182332"}" fill-opacity="0.86" stroke="{stroke}" stroke-width="{3 if robot_here else 1}"/>')
            text(x+16,y+30,label(room),'room',None if known else '#7f8c9e')
            subtitle='COLLECTION POINT' if room==self.target else ('OUTDOORS' if room in ('garden','terrace') else 'ROOM')
            text(x+16,y+49,subtitle,'tiny')
            if not known: text(x+16,y+69,'Room fact missing','tiny','#f3bb71')
            if robot_here:
                # Robot drawn as vector geometry rather than font-dependent emoji.
                rx,ry=x+16,y+80
                if self.actor_image:
                    out.append(f'<image xlink:href="{self.actor_image}" x="{x+7}" y="{y+60}" width="78" height="84" preserveAspectRatio="xMidYMid meet"/>')
                else:
                    out.append(f'<g transform="translate({rx},{ry})"><path d="M22 0V8" stroke="#e9bd70" stroke-width="3"/><circle cx="22" cy="0" r="3" fill="#f4c772"/><rect y="8" width="44" height="29" rx="7" fill="#e9bd70"/><circle cx="13" cy="21" r="4" fill="#152535"/><circle cx="31" cy="21" r="4" fill="#152535"/><rect x="6" y="41" width="32" height="17" rx="4" fill="#8eadd1"/></g>')
                text(x+88,y+98,label(self.actor),'body')
                status=('Holding '+', '.join(label(o) for o in sorted(s['held'],key=str))) if s['held'] else ('Empty-handed' if s['empty'] else 'Hand status unknown')
                # Split long held-object text into per-object lines.
                if s['held']:
                    for i,obj in enumerate(sorted(s['held'],key=str)):
                        text(x+88,y+119+i*16,'Held: '+label(obj),'tiny','#f4c772')
                else: text(x+88,y+119,status,'tiny')
            residents=[o for o in sorted(s['objects'],key=str)
                       if s['positions'].get(o,set())=={room} and o not in s['held']]
            # Standard scenario has up to three objects together in the foyer.
            for i,obj in enumerate(residents[:3]):
                yy=y+146+i*16
                color='#f4c772' if obj in s['evidence'] else '#a8bbda'
                out.append(f'<circle cx="{x+21}" cy="{yy-4}" r="4" fill="{color}"/>')
                text(x+33,yy,label(obj),'tiny',color)
            if len(residents)>3: text(x+148,y+178,f'+{len(residents)-3} more','tiny')
        # Side panel is a complete roster, including unknown/conflicting items.
        out.append('<rect x="1200" y="110" width="364" height="710" rx="16" fill="#18283d"/>')
        text(1220,145,'EVIDENCE & STATUS','room')
        delivered=sum(s['positions'].get(o,set())=={self.target} and o not in s['held'] for o in s['evidence'])
        text(1220,174,f'{delivered} / {len(s["evidence"])} evidence items at {label(self.target)}','body','#e9bd70')
        robot_status=label(robot_room) if robot_room is not None else ('Conflicting locations' if actor_places else 'Unknown location')
        text(1220,209,'Robot: '+robot_status,'body')
        for i,obj in enumerate(sorted(s['objects'],key=str)):
            y=245+i*72
            text(1220,y,label(obj),'body','#f4c772' if obj in s['evidence'] else '#e9edf6')
            text(1220,y+23,s['statuses'][obj],'body')
        # Warnings are wrapped with standard library; cap visible lines, report overflow.
        import textwrap
        messages=list(s['warnings'])
        if not actor_places: messages.insert(0,'Robot location is unknown; held items cannot be placed on the map.')
        unknown=[label(o) for o,status in s['statuses'].items() if status=='Unknown location']
        if unknown: messages.append('Missing locations: '+', '.join(unknown))
        lines=[line for message in messages for line in textwrap.wrap(message,width=40)]
        y=max(560,255+len(s['objects'])*72)
        capacity=max(0,(800-y)//18)
        if lines:
            for i,line in enumerate(lines[:capacity]): text(1220,y+i*18,line,'tiny','#f3bb71')
            if len(lines)>capacity: text(1220,803,'More warnings: see view.inspect(wm, t)','tiny','#f3bb71')
        else:
            text(1220,y,'No display conflicts detected.','tiny','#e9bd70')
        text(36,863,'Gold = evidence   /   Brass arrows = current passages   /   Dashed = reference passage with missing current fact','tiny')
        text(36,885,'Fixed room outlines provide context. Positions never fall back to an earlier step.','tiny')
        out.append('</svg>')
        return SVGFrame(''.join(out))

    def show(self, source, t, title='Ravenwick Manor | The evidence courier', replace=False):
        """Display in Jupyter. replace=True updates this view's previous output."""
        from IPython.display import display
        frame=self.render(source,t,title)
        handle=getattr(self,'_display_handle',None)
        if replace and handle is not None:
            handle.update(frame)
        elif replace:
            self._display_handle=display(frame,display_id=True)
        else:
            display(frame)
        return frame
