import pytest

from src.skill_evolution.shared.unnumbered_patch import apply_patch, actual_diff
from src.skill_evolution.v23.editor import apply_patch as apply_standard

HEADER = '--- a/SKILL.md\n+++ b/SKILL.md\n'
CREATE = '--- /dev/null\n+++ b/SKILL.md\n'
MARK = '\\ No newline at end of file\n'


@pytest.mark.parametrize('source,body,expected', [
    (None, '@@\n+# Skill\n+\n+- Rule\n', '# Skill\n\n- Rule\n'),
    ('', '@@\n+New\n', 'New\n'),
    ('# Skill\n- Old\n- Keep\n', '@@\n # Skill\n-- Old\n+- New\n - Keep\n', '# Skill\n- New\n- Keep\n'),
    ('A\nB\n', '@@\n+Start\n A\n', 'Start\nA\nB\n'),
    ('A\nB\n', '@@\n A\n+Middle\n B\n', 'A\nMiddle\nB\n'),
    ('A\nB\n', '@@\n B\n+End\n', 'A\nB\nEnd\n'),
    ('A\nB\nC\n', '@@\n-B\n', 'A\nC\n'),
    ('A\nB\nC\nD\n', '@@\n-A\n+X\n+Y\n@@\n-D\n+Z\n', 'X\nY\nB\nC\nZ\n'),
    ('same\nanchor\nsame\n', '@@\n anchor\n-same\n+last\n', 'same\nanchor\nlast\n'),
    (' A \r\nB\r\n', '@@\n- A \r\n+ X \r\n B\r\n', ' X \r\nB\r\n'),
    ('A\u2028B\nC\n', '@@\n-C\n+D\n', 'A\u2028B\nD\n'),
    ('A\nB', '@@\n-A\n+X\n', 'X\nB'),
    ('Old', '@@\n-Old\n'+MARK+'+New\n'+MARK, 'New'),
    ('Old', '@@\n-Old\n'+MARK+'+Old\n', 'Old\n'),
    ('Old\n', '@@\n-Old\n+Old\n'+MARK, 'Old'),
    (None, '@@\n+New\n'+MARK, 'New'),
    ('a\r', '@@\n-a\r\n'+MARK+'+b\r\n'+MARK, 'b\r'),
])
def test_exact_edits_and_independent_standard_diff(source, body, expected):
    value = apply_patch(source, (CREATE if source is None else HEADER) + body)
    assert value == expected
    assert apply_standard(source, actual_diff(source, value)) == expected


@pytest.mark.parametrize('source,body,error', [
    ('A\n', '@@ -1 +1 @@\n-A\n+B\n', 'bare @@'),
    ('A\n', '@@ note\n-A\n+B\n', 'bare @@'),
    ('A\n', '@@\nA\n+B\n', 'body line'),
    ('A\n', '@@\n-A\n+B', 'body line'),
    ('A\n', '@@\n+A\n', 'requires context'),
    ('A\n', '@@\n-Wrong\n+B\n', 'found 0'),
    ('same\nsame\n', '@@\n-same\n+new\n', 'found 2'),
    ('A \n', '@@\n-A\n+B\n', 'found 0'),
    ('A\r\n', '@@\n-A\n+B\n', 'found 0'),
    ('XA\n', '@@\n-A\n+B\n', 'found 0'),
    ('A\nB\n', '@@\n-B\n+X\n@@\n-A\n+Y\n', 'order'),
    ('A\nB\nC\n', '@@\n-A\n+X\n B\n@@\n B\n-C\n+Y\n', 'overlaps'),
    ('A\nB\n', '@@\n-A\n+X\n@@\n-X\n+Y\n', 'Hunk 2.*found 0'),
    ('A\nB\n', '@@\n-A\n+X\n@@\n-Wrong\n+Y\n', 'Hunk 2.*found 0'),
    ('A\n', '@@\n A\n', 'actual change'),
    ('A\n', '@@\n-A\n+A\n', 'actual change'),
    ('A\n', '@@\n-A\n', 'empty or unchanged'),
    ('A\n', '@@\n-A\n+  \n', 'empty or unchanged'),
    ('A', '@@\n-A\n+B\n', 'found 0'),
    ('A\nB\n', '@@\n-A\n+X\n'+MARK, 'before result EOF'),
    ('A\n', '@@\n-A\n+X\n'+MARK+'+Y\n', 'before fragment EOF'),
    ('A\n', '@@\n-A\n+B\n'+MARK+MARK, 'body line'),
    (None, '@@\n+A\n@@\n+B\n', 'one addition-only'),
])
def test_reject_without_repair(source, body, error):
    with pytest.raises(ValueError, match=error):
        apply_patch(source, (CREATE if source is None else HEADER) + body)


@pytest.mark.parametrize('source,patch', [
    (None, HEADER+'@@\n+A\n'),
    ('A\n', CREATE+'@@\n+B\n'),
    ('A\n', HEADER.replace('a/SKILL.md', 'a/OTHER.md')+'@@\n-A\n+B\n'),
    ('A\n', HEADER+'@@\n-A\n+\0\n'),
    ('A\n', HEADER+'@@\n-A\n+\ud800\n'),
])
def test_headers_and_encoding(source, patch):
    with pytest.raises(ValueError):
        apply_patch(source, patch)
