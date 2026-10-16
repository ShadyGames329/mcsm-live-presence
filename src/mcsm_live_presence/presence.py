"""Format only live values; never infer progress from save files."""
import re

EPISODES = {
    1: 'The Order of the Stone', 2: 'Assembly Required',
    3: 'The Last Place You Look', 4: 'A Block and a Hard Place',
    5: 'Order Up!', 6: 'A Portal to Mystery', 7: 'Access Denied',
    8: "A Journey's End?",
}


def make_payload(event, *, start, config):
    mode = event.get('mode', 'unknown') if event else 'unknown'
    details = {'menu': 'Main Menu', 'browsing': 'Browsing Episodes',
               'gameplay': 'Playing', 'paused': 'Paused'}.get(mode, 'Minecraft: Story Mode')
    state = 'In session' if mode == 'unknown' else 'Minecraft: Story Mode'
    episode = None
    if mode == 'gameplay' and event:
        value = event.get('episode', '')
        if value in tuple(str(n) for n in EPISODES):
            episode = int(value)
            details = f'Episode {episode}: {EPISODES[episode]}'
        pieces = []
        chapter = re.fullmatch(r'(?:10([1-8])_chapter)?([1-9]\d?)[a-z]?', event.get('chapter', ''), re.I)
        if chapter and (not chapter.group(1) or episode == int(chapter.group(1))):
            pieces.append(f'Chapter {int(chapter.group(2))}')
        scene = event.get('scene', '')
        if scene and config.get('show_scene', True):
            scene = re.sub(r'\.(lua|scene)$', '', scene, flags=re.I)
            scene = re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', scene).replace('_', ' ')
            pieces.append(scene)
        if pieces:
            state = ' | '.join(pieces)
    result = {'details': details[:128], 'state': state[:128], 'start': start}
    image = config.get('large_image_key', '')
    if episode:
        image = config.get('episode_image_keys', {}).get(str(episode), image)
    if image:
        result.update(large_image=image, large_text='Minecraft: Story Mode')
    return result
