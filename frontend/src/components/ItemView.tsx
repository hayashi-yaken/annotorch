import { api } from "../api";
import type { Item } from "../api";

export default function ItemView({ projectId, item, size }: {
  projectId: string; item: Item; size?: "large";
}) {
  if (item.modality === "image") {
    return (
      <img
        className="item-thumb"
        style={size === "large" ? { height: 260 } : undefined}
        src={api.itemFileUrl(projectId, item.id)}
        alt={item.id}
      />
    );
  }
  return (
    <div className="card" style={size === "large" ? { fontSize: "1.15rem" } : undefined}>
      {item.text}
    </div>
  );
}
