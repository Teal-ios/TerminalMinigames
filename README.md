# 🎮 Terminal Minigames

터미널에서 즐기는 **똥피하기 · 우주선 슈팅 · 피카츄풍 배구**. 게임을 폴더 단위로 추가하는 플러그인 방식의 작은 오락실입니다.

Python 표준 라이브러리만 사용하므로 별도 패키지 설치가 필요 없습니다.

## 준비 사항

- macOS 또는 Linux의 키보드 입력이 가능한 터미널
- Python **3.9 이상**: `python3 --version`으로 확인
- 터미널 크기 **66칸 × 33줄 이상** 권장
- Windows에서는 WSL의 Linux 터미널을 사용하세요. Windows 기본 Python은 지원 대상이 아닙니다.

문자 정렬을 위해 게임 화면은 ASCII로 표현합니다. 배구는 원작 이미지·음원을 사용하지 않는 피카츄 배구풍 팬 게임입니다.

## 빠른 시작

```sh
git clone https://github.com/Teal-ios/TerminalMinigames.git
cd TerminalMinigames
./arcade
```

번호 또는 게임 ID를 입력해 선택하세요. 게임 종료 후에는 셸로 돌아옵니다.

```sh
./arcade list     # 게임 목록
./arcade poop     # 똥피하기
./arcade space    # 우주선 슈팅
./arcade volley   # 피카츄풍 배구
./arcade --help   # 도움말
```

현재 작업 폴더에서는 다음과 같이 실행합니다.

```sh
cd /Users/runningpoint/Desktop/Test
./arcade
```

실행 권한이 없는 환경에서는 `python3 arcade`도 가능합니다.

## 어느 폴더에서나 `arcade`로 실행

저장소 폴더에서 다음 명령을 실행하면 **현재 터미널 세션**에서 사용할 수 있습니다.

```sh
export PATH="$PWD:$PATH"
arcade list
arcade space
```

새 터미널에서도 사용하려면 셸 설정 파일(macOS 기본 셸: `~/.zshrc`, Bash: `~/.bashrc`)에 **실제 저장소 절대 경로**를 추가하고 새 터미널을 여세요. 현재 작업 위치의 예시:

```sh
export PATH="/Users/runningpoint/Desktop/Test:$PATH"
```

저장소 위치를 옮기면 설정된 경로도 바꿔주세요.

## 조작법

공통: **R** 다시 시작, **P** 일시정지/계속하기, **Q / Esc / Ctrl+C** 종료.

### 💩 똥피하기 — `arcade poop`

`@`를 움직여 떨어지는 `*`을 피하세요. 생존 시간에 따라 점수가 오르며 12초마다 난이도가 높아집니다. 최고 점수는 해당 실행 중에만 유지됩니다.

| 키 | 동작 |
|---|---|
| Enter / Space | 시작 |
| ← / → 또는 A / D | 이동 |
| Space / P | 일시정지/계속하기 |

최소 화면 크기는 48칸 × 29줄입니다.

### 🚀 우주선 슈팅 — `arcade space`

`/A\`를 조종해 적 `\V/`을 격추하세요. 적당 100점, 500점마다 난이도가 올라갑니다. 목숨은 3개입니다. 적·탄환과 충돌하거나 적을 아래로 놓치면 목숨이 줄며, 피격 후 1.5초간 무적입니다.

| 키 | 동작 |
|---|---|
| Enter | 시작 |
| 방향키 / WASD | 이동 |
| Space | 발사 |
| F | 자동 발사 켜기/끄기 |

터미널에서는 **F로 자동 발사를 켜고 이동**하면 편합니다.

### ⚡ 피카츄풍 배구 — `arcade volley`

왼쪽 노란 캐릭터가 플레이어, 오른쪽 초록 캐릭터가 컴퓨터입니다. 공 아래로 이동하면 자동으로 받아칩니다. 상대 코트에 공을 떨어뜨려 **5점을 먼저 얻으면 승리**합니다. 벽·천장에서는 공이 튕기고 서브는 자동 진행됩니다.

| 키 | 동작 |
|---|---|
| Enter | 시작 |
| ← / → 또는 A / D | 이동 |
| ↑ / W | 점프 |
| Space | 점프 + 스파이크 준비 (0.4초) |

공에 닿을 순간 Space를 누르세요. 네트보다 높은 위치에서 스파이크하면 공을 아래로 내려칩니다.

## 새 게임 플러그인 추가

`games/<게임 폴더>/`에 `game.json`과 Python 실행 파일을 추가하면 자동으로 목록에 나타납니다. 실행기 수정이나 별도 등록은 필요 없습니다.

```text
arcade                 # 실행 명령
arcade_cli.py          # 플러그인 검색과 선택 메뉴
arcade_screen.py       # 공통 터미널 화면과 실행 루프
games/
  poop/                # 각 게임에 game.json, game.py
  space/
  volley/
  my-game/             # 여기에 새 게임 추가
```

`games/my-game/game.json`:

```json
{
  "id": "my-game",
  "name": "내 새 게임",
  "description": "게임 한 줄 소개",
  "entry": "game.py"
}
```

`games/my-game/game.py` 최소 예시:

```python
def main():
    print("새 게임 실행!")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

```sh
./arcade list
./arcade my-game
```

- `id`는 소문자 영문으로 시작하고 소문자 영문·숫자·하이픈을 사용합니다. 다른 게임 ID와 중복되거나 `list`일 수 없습니다.
- `entry`는 해당 게임 폴더 안의 `.py` 파일을 가리키는 상대 경로입니다.
- 게임은 현재 Python의 별도 프로세스로 실행됩니다. 작업 디렉터리는 실행 파일이 있는 폴더입니다.
- 잘못된 플러그인 설정은 경고 후 건너뛰어 다른 게임을 계속 사용할 수 있습니다.
- 로컬 Python 코드를 실행하므로 직접 만들었거나 신뢰하는 플러그인을 추가하세요.

공통 화면을 사용하려면 `games/space/game.py`와 `games/volley/game.py`의 `handle`, `update`, `draw`와 `arcade_screen.run` 사용법을 참고하세요. 자체 터미널 루프를 쓰는 게임도 추가할 수 있습니다.

## 개발 및 테스트

```sh
python3 -m unittest -v
```

플러그인 발견·설정 오류 격리·실행 경로 검증·종료 코드 전달과 슈팅 충돌·배구 반사·득점 규칙을 검사합니다.

## 사용 팁

- 화면 크기 안내가 나오면 창을 넓히거나 글꼴을 줄여주세요. 창이 작은 동안 게임은 멈춥니다.
- 키를 누르고 있을 때의 이동 속도는 OS와 터미널의 키 반복 설정에 따릅니다. 입력이 안 되면 영문 입력으로 전환하세요.
- IDE 출력 전용 창 대신 Terminal, iTerm2, VS Code 통합 터미널 등에서 실행하세요.
- 정상 종료 시 터미널 설정을 복원합니다. 강제 종료 후 화면이 이상해졌다면 셸에서 `reset`을 실행하세요.
