import React from "react";
import { describe, expect, it } from "vitest";
import ChatSessionPage from "../app/c/[token]/page";

function collectThenableProps(node: React.ReactNode, path = "root"): string[] {
  if (!React.isValidElement(node)) {
    return [];
  }

  const props = node.props as Record<string, unknown>;
  const ownThenableProps = Object.entries(props)
    .filter(([key, value]) => key !== "children" && typeof (value as { then?: unknown } | null)?.then === "function")
    .map(([key]) => `${path}.${key}`);

  return [
    ...ownThenableProps,
    ...React.Children.toArray(props.children as React.ReactNode).flatMap((child, index) =>
      collectThenableProps(child, `${path}.children[${index}]`),
    ),
  ];
}

describe("ChatSessionPage", () => {
  it("unwraps dynamic route promises before passing props to client components", async () => {
    const tree = await ChatSessionPage({
      params: Promise.resolve({ token: "new" }),
      searchParams: Promise.resolve({ mode: "build" }),
    });

    expect(collectThenableProps(tree)).toEqual([]);
  });
});
