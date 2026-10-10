"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, UserPlus } from "lucide-react";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { RoleBadge } from "@/components/role-badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { api } from "@/lib/api";
import { initials, timeAgo } from "@/lib/format";
import type { User } from "@/lib/types";

export function UsersPanel({ currentUserId }: { currentUserId: number }) {
  const queryClient = useQueryClient();
  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api<User[]>("/users"),
  });

  const toggleActive = useMutation({
    mutationFn: (u: User) =>
      api<User>(`/users/${u.id}`, { method: "PATCH", json: { is_active: !u.is_active } }),
    onSuccess: (u) => {
      toast.success(`${u.full_name} ${u.is_active ? "enabled" : "disabled"}`);
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1.5">
          <CardTitle>Users</CardTitle>
          <CardDescription>
            Admins manage assets and run scans; auditors have read-only access.
          </CardDescription>
        </div>
        <AddUserDialog />
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>User</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Last sign-in</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading &&
              Array.from({ length: 2 }, (_, i) => (
                <TableRow key={i}>
                  <TableCell colSpan={5}>
                    <Skeleton className="h-8 w-full" />
                  </TableCell>
                </TableRow>
              ))}
            {users?.map((u) => (
              <TableRow key={u.id}>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <Avatar className="size-8">
                      <AvatarFallback className="text-xs">{initials(u.full_name)}</AvatarFallback>
                    </Avatar>
                    <div className="grid leading-tight">
                      <span className="font-medium">
                        {u.full_name}
                        {u.id === currentUserId && (
                          <span className="ml-1.5 text-xs font-normal text-muted-foreground">(you)</span>
                        )}
                      </span>
                      <span className="text-xs text-muted-foreground">{u.email}</span>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <RoleBadge role={u.role} />
                </TableCell>
                <TableCell>
                  {u.is_active ? (
                    <Badge variant="outline" className="gap-1.5">
                      <span className="size-1.5 rounded-full bg-primary" />
                      Active
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-muted-foreground">
                      Disabled
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {u.last_login_at ? timeAgo(u.last_login_at) : "Never"}
                </TableCell>
                <TableCell className="text-right">
                  {u.id !== currentUserId && (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={toggleActive.isPending}
                      onClick={() => toggleActive.mutate(u)}
                    >
                      {u.is_active ? "Disable" : "Enable"}
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

const newUserSchema = z.object({
  full_name: z.string().trim().min(2, "Enter the full name"),
  email: z
    .string()
    .trim()
    .regex(/^[^@\s]+@[^@\s]+\.[^@\s]+$/, "Enter a valid email address"),
  password: z.string().min(8, "At least 8 characters"),
  role: z.enum(["admin", "auditor"]),
});
type NewUser = z.infer<typeof newUserSchema>;

function AddUserDialog() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const form = useForm<NewUser>({
    resolver: zodResolver(newUserSchema),
    defaultValues: { full_name: "", email: "", password: "", role: "auditor" },
  });
  const { errors } = form.formState;

  const create = useMutation({
    mutationFn: (values: NewUser) => api<User>("/users", { method: "POST", json: values }),
    onSuccess: (u) => {
      toast.success(`${u.full_name} added`);
      queryClient.invalidateQueries({ queryKey: ["users"] });
      queryClient.invalidateQueries({ queryKey: ["audit-log"] });
      form.reset();
      setOpen(false);
    },
    onError: (e) => toast.error(e.message),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <UserPlus />
          Add user
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add user</DialogTitle>
          <DialogDescription>They can sign in immediately with these details.</DialogDescription>
        </DialogHeader>
        <form
          id="add-user"
          onSubmit={form.handleSubmit((v) => create.mutate(v))}
          className="space-y-4"
          noValidate
        >
          <Field label="Full name" error={errors.full_name?.message}>
            <Input id="full_name" {...form.register("full_name")} />
          </Field>
          <Field label="Email" error={errors.email?.message}>
            <Input id="email" type="email" {...form.register("email")} />
          </Field>
          <Field label="Temporary password" error={errors.password?.message}>
            <Input id="password" type="password" {...form.register("password")} />
          </Field>
          <Field label="Role">
            <Controller
              control={form.control}
              name="role"
              render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger id="role" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="auditor">Auditor: read-only access</SelectItem>
                    <SelectItem value="admin">Admin: full access</SelectItem>
                  </SelectContent>
                </Select>
              )}
            />
          </Field>
        </form>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button type="submit" form="add-user" disabled={create.isPending}>
            {create.isPending && <Loader2 className="animate-spin" />}
            Add user
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactElement<{ id?: string }>;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={children.props.id}>{label}</Label>
      {children}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}
