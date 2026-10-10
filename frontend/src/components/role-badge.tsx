import { Badge } from "@/components/ui/badge";
import type { Role } from "@/lib/types";
import { cn } from "@/lib/utils";

export function RoleBadge({ role, className }: { role: Role; className?: string }) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "capitalize",
        role === "admin" && "border-primary/30 bg-primary/10 text-primary",
        className,
      )}
    >
      {role}
    </Badge>
  );
}
