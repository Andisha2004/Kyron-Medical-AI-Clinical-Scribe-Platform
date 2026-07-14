interface StatusBadgeProps {
  label: string;
  status?: "neutral" | "success" | "warning" | "danger";
}

const statusClasses = {
  neutral: "bg-slate-100 text-slate-700",
  success: "bg-emerald-100 text-emerald-800",
  warning: "bg-amber-100 text-amber-800",
  danger: "bg-red-100 text-red-800",
};

export function StatusBadge({ label, status = "neutral" }: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${statusClasses[status]}`}
    >
      {label}
    </span>
  );
}
