# CC3201Bot

## CC3201 - Databases

Discord Bot for supporting the CC3201 course's lab sessions.

It helps with the following features:

- Add/delete group channels (including voice and text).
- Limit other groups' access to the other groups
- Provide teacher assistants with useful commands for solving students' questions in a simple way.

Implemented using Python 3.6

[Discord docs](https://discordpy.readthedocs.io/en/latest/api.html)

## How to add bot on a new server

- Add bot via [Discord Developer portal](https://discord.com/developers) with admin permissions (TODO: decrease permissions needed to only the ones the bot needs). 

- Initialize server using command `!init-guild`. This will create 4 key roles: profesor, auxiliar, ayudante, estudiante. These roles **must not** be modified.

- Each group have a text channel and a voice channel where only its members can see and interact in. That means only they have permissions to read and write permissions on both channels. The teaching team have the same permissions along all groups.

- General message (mainly info messages) will be showed on the "text-general" channel.

## How to AidanBot

### Teaching team commands

You have to have one of the following roles: profesor, auxilar or ayudante. Then you will have permissions to see any created group on the server. 

#### Category create/delete groups
`!create-group`: Create new group. Aliases=!cg - !create
`!create-many-groups <n>`: Create n new groups. Alias=!cmg
`!delete-all-groups`: Delete all groups.
`!delete-group <group_num>`: Delete the given group. Aliases=!dg - !delete

#### Category make groups
`!move @<name> <group_num>`: Move student to the given group. The @ is to mention other users or members on the server. If the group is closed, the student needs an invitation beforehand.

`!make-group @<name_1> ... @<name_n>`\*: Assign the designated students to a open group. If there are no open groups, a new one will be created. The command fails if you include more students than the allowed limit or if you include a member that doesn't exist. Aliases= mk - !group

*Note*: Students can join to a group only if have set their nickname. The reason of this restriction is for when the command `!list` is used it can deliver the list of students quickly. Besides, each group can have up to three people, excluding the teaching team's members.

To be continue...



