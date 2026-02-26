---
name: priority-stabilizer
description: This skill should be used when users express uncertainty about task priorities, worry about abandoning important work, or face conflicts between ongoing projects and urgent interruptions. It analyzes the structure of competing priorities, determines if sudden shifts are driven by fear or genuine urgency, and provides a clear, immediate action to take. The skill does not ask follow-up questions—it delivers a one-shot decision based on the provided context.
---

# Priority Stabilizer

## Overview

このスキルは、突発的な優先順位の入れ替わりを検出し、元々の意図（Primary）と突発要因（Intruder）を構造化して分析します。恐れ由来の判断を排除し、合理的な優先順位を提示することで、意思決定の安定性を高めます。

## 使用タイミング

このスキルを使用すべき状況:
- 進行中のタスクがあるが、別のタスクが気になり始めた時
- 「今これをやるべきか?」という優先順位の迷いが生じた時
- 複数のタスク間で揺れ動いている時
- 緊急性と重要性の判断が曖昧な時

## 分析フレームワーク

### 評価軸

優先順位を判断する際、以下の4つの軸で評価します:

1. **長期影響度** - 長期的な目標達成への寄与度
2. **緊急性** - 時間的制約の強さ
3. **可逆性** - 後から対処可能かどうか
4. **恐れ由来か** - 不安や恐れが動機になっているか

### 決定ルール

以下のルールに基づいて優先順位を決定します:

1. **緊急×不可逆** → Intruder優先
   - 時間制約があり、後から対処できない場合は即座に対応

2. **恐れ×可逆** → Primary維持
   - 不安から来る衝動で、後でも対処可能な場合は元の計画を維持

3. **不確実** → Primary維持 + Intruderを5分処理
   - 判断が難しい場合は、Intruderに5分だけ投資して実態を把握し、再判断

## 出力フォーマット

分析結果は以下の4セクション構造で出力します:

### 1) 構造

```markdown
**Primary (元々の意図)**: [進行中だったタスク・目的]
**Intruder (突発要因)**: [割り込んできた懸念・タスク]
```

元々進めていた意図と、それを脅かす突発的な要因を明確に分離します。

### 2) 乗っ取り判定

```markdown
**動機**: [fear/urgency/opportunity のいずれか]
**恐れ由来度**: [High/Mid/Low]
```

Intruderが恐れから来ているか、本当に緊急なのかを判定します。

### 3) 今の優先順位

```markdown
**結論**: [Primary優先 / Intruder優先 / 5分だけIntruder]
**理由**: [1-2文で簡潔に]
```

評価軸と決定ルールに基づき、どちらを優先すべきか明確に示します。

### 4) 今すぐやる1つ

```markdown
[具体的な次の1アクション。5-15単語程度]
```

考えすぎず行動できるよう、明確で実行可能な1つの行動を提示します。

## 実行上の注意

### 追加質問の禁止

このスキルは1発回答型です。ユーザーに追加の情報を求めることなく、提供された情報のみで判断を完結させます。

### 簡潔性の重視

各セクションは簡潔に保ちます:
- 構造: 各1行
- 乗っ取り判定: 2行
- 今の優先順位: 結論1行+理由1-2文
- 今すぐやる1つ: 1行(5-15単語)

総文字数は200-400文字程度を目安とします。

### 不確実性への対処

情報が不足している場合でも、可能性の高い仮説を立てて判断します。その際は「おそらく」「推測では」などの言葉を使い、不確実性を明示します。

## 使用例

**ユーザー入力:**
```
コーディング中だけど、メールの返信が気になってきた。
すぐ返さないと失礼かも...
```

**出力:**
```markdown
### 1) 構造
**Primary**: コーディング作業の継続
**Intruder**: メール返信への焦り

### 2) 乗っ取り判定
**動機**: fear
**恐れ由来度**: High

### 3) 今の優先順位
**結論**: Primary維持
**理由**: メールは可逆的タスク。恐れ由来の緊急性であり、コーディングのフロー状態を壊すコストの方が大きい。

### 4) 今すぐやる1つ
コードを次のブレークポイントまで書き切る
```

## カスタマイズ

このスキルの判定ルールは、ユーザーの価値観や状況に応じて調整可能です。特に以下の要素は個人差が大きいため、必要に応じて変更してください:

- 「恐れ由来」の判定基準
- 緊急性の閾値
- 「5分処理」の時間設定

