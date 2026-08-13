import { useState } from "react";
import { assignToGroup, groupsToAnswer } from "../../lib/groupstate";
import ItemView from "../ItemView";
import type { EditorProps } from "./types";

const COLORS = ["#4a7", "#47a", "#a47", "#a74", "#7a4", "#74a"];

export default function Grouping({ projectId, unit, onSave }: EditorProps) {
  const [numGroups, setNumGroups] = useState(2);
  const [active, setActive] = useState(0);
  const [assignment, setAssignment] = useState<Record<string, number>>({});
  const answer = groupsToAnswer(unit.items.map((i) => i.id), assignment);

  return (
    <div>
      <p>グループを選んでからアイテムをクリックして振り分ける</p>
      <div className="row">
        {Array.from({ length: numGroups }, (_, g) => (
          <button key={g}
                  style={{
                    border: `${active === g ? 3 : 1}px solid ${COLORS[g % COLORS.length]}`,
                  }}
                  onClick={() => setActive(g)}>
            グループ {g + 1}
          </button>
        ))}
        <button onClick={() => setNumGroups(numGroups + 1)}>＋ グループ追加</button>
      </div>
      <div className="grid">
        {unit.items.map((item) => {
          const g = assignment[item.id];
          return (
            <div key={item.id} className="clickable"
                 style={g !== undefined
                   ? { outline: `3px solid ${COLORS[g % COLORS.length]}` }
                   : undefined}
                 onClick={() => setAssignment(assignToGroup(assignment, item.id, active))}>
              <ItemView projectId={projectId} item={item} />
              <div>{g !== undefined ? `グループ ${g + 1}` : "未割当"}</div>
            </div>
          );
        })}
      </div>
      <div className="row">
        <button className="big" disabled={!answer}
                onClick={() => answer && onSave({ groups: answer })}>
          保存して次へ
        </button>
        <button onClick={() => setAssignment({})}>リセット</button>
      </div>
    </div>
  );
}
