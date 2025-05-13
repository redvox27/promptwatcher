# Findings

## Overview

In this document, I’ll share the main issues I ran into while working with Claude and how I eventually overcame them. For reference, also see `own-fixed.md`.

## 1. Claude tends to ignore instructions

One of the biggest challenges I faced early on was that Claude has a very active imagination—and it loves to show it. Give it a simple instruction to fix a bug, and it might respond with 100 lines of code including new features you never asked for. Even when requesting a basic feature, Claude often adds 10 extra things you didn’t want.

This forced me to reset my codebase back to the last working skeleton multiple times, because it became impossible to keep track of what had been added versus what still needed to be done. That brings me to the next point.

## 2. Use Git. A lot.

I’ve always used Git regularly, but working with AI made it even more essential. It allows you to easily revert to the last working version when things go sideways.

There were several moments where I completely lost control of Claude’s "creativity." It wrote features I didn’t ask for, introduced bugs that didn’t need to exist, and left me confused about why certain code was even there. After three full resets, I knew I had to try something different.

## 3. Read the official prompting guides

I highly recommend reading the official Claude documentation:  
👉 [Claude Code Best Practices by Anthropic](https://www.anthropic.com/engineering/claude-code-best-practices)  
👉 [Prompting Guide by Google](https://drive.google.com/file/d/1AbaBYbEa_EbPelsT40-vj64L-2IwUJHy/view?pli=1)

These helped a lot. But even after applying their tips, I still couldn’t fully stop Claude from going off-track and adding random stuff. Which brings me to point 4.

## 4. Break tasks down into baby steps

For example, I once had a simple error due to a missing attribute—something that could be fixed by referencing a class properly. But if I asked Claude to “fix the error,” it would likely write the full implementation for that part of the system, even though I wasn’t ready for that.

Instead, I traced the error, found the root cause, and gave Claude a very specific instruction:  
> "Please fix only the reference error on line X in class C. Do not write or update any implementation code."

This worked well and kept things under control.

## 5. Tell Claude what *not* to do

This is a major point in the official guide too: don’t just tell Claude what to do—be clear about what **not** to do. That’s the only way to keep its creative output in check. Be specific. Claude listens better when you set clear boundaries.

## 6. Ask Claude to write a plan before coding

Even after trying everything above, I still struggled with the same issue: Claude writes code for features I didn’t ask for, or goes overboard with the ones I did request. The implementations often became so large that I lost track of what was done, and what was still missing.

I used to ask Claude to list what features had been implemented and what was still left—based on our architecture docs and TODO lists—but I still felt like I wasn’t in full control.

What finally helped was this:

Before asking Claude to implement anything, I asked it to write a **step-by-step plan** for that specific feature. Then I asked for a new TODO list based on that plan. Game-changer.

Now I can tell Claude,  
> "Please implement steps X, Y, and Z from the plan."

Once I’ve tested those, I can move on to the next ones. No more surprise features. I finally feel in control of the build process, and I actually know what’s being developed—and why.
