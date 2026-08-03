"use client";

import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";

import { cn } from "@/lib/utils";

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn("inline-flex h-9 items-center gap-1 rounded-md bg-muted p-1", className)}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex flex-1 items-center justify-center rounded-sm px-2 py-1 text-xs font-medium text-muted-foreground transition-colors",
      "data-[state=active]:bg-card data-[state=active]:text-foreground data-[state=active]:shadow-sm",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  // `data-[state=inactive]:hidden` matters, not just cosmetic: Radix sets
  // the native `hidden` attribute on inactive panels, but the browser's
  // built-in `[hidden] { display: none }` rule is author-overridable, and
  // every caller in this app also passes `flex` in `className` (e.g.
  // right-panel.tsx's `"flex min-h-0 flex-col pt-2"`) — `display: flex`
  // from that class was winning over the UA `[hidden]` rule, so all three
  // right-panel tabs (Sources/Artifacts/Research) stayed in the flex
  // layout at once and split the available height three ways (~1/3 each)
  // instead of the active one getting the full height. This explicit
  // variant utility forces `display: none` on inactive panels regardless
  // of whatever `display` utility a caller's className adds.
  <TabsPrimitive.Content
    ref={ref}
    className={cn("flex-1 overflow-hidden data-[state=inactive]:hidden", className)}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
