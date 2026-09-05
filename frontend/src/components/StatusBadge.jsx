import { statusClasses } from "../utils/format";

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-block rounded-full px-2.5 py-1 text-xs font-medium ${statusClasses(status)}`}>
      {status?.replaceAll("_", " ")}
    </span>
  );
}