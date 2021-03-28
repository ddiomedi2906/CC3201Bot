# CC3201Bot

## Bot for Labs

Discord Bot for supporting group work in courses. 

Originally made for CC3201 labs (Databases).

It helps with the following features:

- Add/delete group channels (including voice and text).
- Limit other groups' access to the other groups
- Provide teaching assistants with useful commands for solving students' questions in a simple way.

Implemented using Python 3.6

[Discord docs](https://discordpy.readthedocs.io/en/latest/api.html)

## Create a new Discord server

You can add the bot to an existing server, but to create a new server:

- Log into Discord. On the home screen, you should find a large green plus icon on the left under the list of your servers with the text `Add New Server`. Click and fill in the details.

## Create a new bot

- Log into Discord and go to the [Discord Developer portal](https://discord.com/developers).

- Click on the `New Application`  button and give your application a name.

- Go the `Bot` tab on the left and then click on the `Add Bot` button. Use the following settings.

```
Public bot: No
Requires OAuth2: No
Presence Intent: Yes
Server Members Intent: Yes
```

- Copy the token and keep it handy. (The token you should keep private but you will need it later.)

Your bot is now ready (or at least its shell is ready).

## Add the bot to the server

- Go to the `OAuth2` tab on the left and tick (only) the `bot` box under `SCOPES`.

- Under `BOT PERMISSIONS` chose `Administrator`. (TODO: decrease permissions needed to only the ones the bot needs.) 

- Copy the URL above the permissions and paste it into your browser. Then select the server you want to add the bot to.

If you go to your server, you should see your bot appear. It cannot do all that much until we connect it with our code. But you can be friendly and say hello with `!salute`.

## Create a test Discord server

A test server is used for logging messages and configurations. (TODO: It is not clear how necessary this step is: remove?)

- Create a new Discord server.

- Copy the ID for the server (if you cannot see enable `Developer Mode` in `User Settings > Appearance`; then right click the server icon on the right and click `Copy ID`).

- Add your bot to this server as well using the same steps seen previously.

## Run the code for the bot

- You should have `git`, `python3` and `pip` installed on the machine that will run the bot's logic.

- Install the following libraries if you don't already have them.

```
python3 -m pip install -U discord.py
python3 -m pip install python-dotenv
```

- Grab the code from this repository.

```
git clone https://github.com/aidhog/CC3201Bot
```

- In the `CC3201Bot` folder, create a (hidden) file called `.env`. Add the following settings, ensuring to replace `XXXX` with the Discord token you copied earlier, and `YYYY` with the test server ID you copied earlier.

```
DISCORD_TOKEN=XXXX
DISCORD_TEST_GUILD_ID=YYYY
PROFESSOR_ROLE_NAME=Profesor
AUXILIAR_ROLE_NAME=Auxiliar
ASSISTANT_ROLE_NAME=Ayudante
STUDENT_ROLE_NAME=Estudiante
GENERAL_TEXT_CHANNEL_NAME=text-general
GENERAL_VOICE_CHANNEL_NAME=voice-general
PRIVATE_TEXT_CHANNEL_NAME=text-private
PRIVATE_VOICE_CHANNEL_NAME=voice-private
MAX_STUDENTS_PER_GROUP=3
REQUIRE_NICKNAME=True
BROADCAST_TO_EMPTY_GROUPS=True
```

- You can try to change some settings such as max students per group, but this would be untested. Some settings refer to channels that we define in the next step.

- Run the bot with the `python3 bot.py` command and leave it running (you can append `&` on some systems to run it in the background). If you see a `KeyError` don't worry for now. It's a connection issue with the test server. We will configure it soon.

- If you try `!help` in the server with the bot, you should see some new commands.

## Prepare your server

These are instructions for how we have set up the server in CC3201, CC5212, CC7220, etc.

- Go to your server on Discord with the bot running.

- Initialise server using command `!init-guild`. This will create 4 key roles: Profesor, Auxiliar, Ayudante, Estudiante. These roles **must not** be modified.

- Right click on your name and give yourself the role Profesor (or Auxiliar).

- You will need to set roles for Auxiliares, Ayudantes, etc., in the same way once they enter the server. The default role is Estudiante.

- Create categories Private and General.

- Under Private create text channel `text-private` and voice channel `voice-private`. Right click on `Private Category` > `Edit` > `Permissions`, make private, and check that `Profesor`, `Auxiliar`, `Ayudante` have access. Only the teaching team will have access here.

- Under General create text channel `text-general` and voice channel `voice-general`.

- You might want to consider removing any default channels or categories that you will not use (the default channels and categories will be a bit redundant under this setup, but you can leave any existing channels you need).

- Now we can create the groups and their channels. Choose how many groups you want. More can be added later. Here we will initialise 50 but you can create up to 99 groups (maybe more?). Run `!create-many-groups 50` in your server. Note that it might take some minutes.

Now each group has a text channel and a voice channel, both restricted to its members. Only they have permissions to read and write permissions on both channels. The teaching team can access any group and can see historical messages. Students who join the same group later may say historical messages in the chat. Thus the chat should be considered as restricted and should not be considered as private for the group.

## Prepare your test server

- Go to your test server on Discord with the bot running.

- Initialise server using command `!init-guild`.

- Remove whatever channels or categories are on the server.

- Create the category `General`.

- Under General create text channel `text-general` and voice channel `voice-general`.

The next time you run the bot the `KeyError` exception should disappear.

## Inviting people to the server

You can invite people to join the server.

- Right click on `text-general`, then `Invite People`. Copy the invite URL and share it with those you wish to invite.

- Don't forget to set roles for ayudantes and auxiliares by right clicking their name when they join, and using the `Roles` menu item. You should not leave professores, auxiliares or ayudantes with the `Estudiante` role as otherwise they might be considered as members of groups, assigned to groups, etc.

- Those interacting with the bot must have a nickname set on the server. They can do this by right clicking on their own name in the list on the right hand side and selecting `Change Nickname`. If you want to match users with students, be sure to ask them to set their nicknames to their real names. Until a nickname is set, many features will be unavailable. The reason for this restriction is so that when the command `!list` is used it can deliver the list of students quickly. Make sure to let them know about this when you invite them to a group. (In any case, they will receive messages from the bot to tell them to add their nickname if needed.)

## Shutting down the bot

If you want to shut down the bot, call `!save-guild` beforehand. It will remember some settings like which groups are open and which are closed.

## How to AidanBot

### The one command you actually need

You can type `!help` to see commands, and `!help list` to see the arguments for a command, in this case the command `!list`. (TODO: may not be displaying all commands.)

### Open vs. closed groups

In the first version of the bot, all groups were open, meaning anyone could join any group. This created some problems as some people wanted to form a particular group, and others joined meanwhile and were asked to leave, etc. So now the bot manages two types of groups. Anyone can join an open group (so long as it has not reached its max number of members). On the other hand, to join a closed group, students need an invitation from someone in the group. 

### Student commands

Students will have the role: Estudiante. They will have limited commands.

#### Joining, leaving, etc., groups

When the students first enter the server, they need to start forming groups. Here are the key commands (typically from `text-general`):

- `!list-open`: See all open groups and their members. Alias=`!og`
- `!group @name1 ... @namek`: Add all members listed to an open group (creating one if necessary and possible).
- `!join group_num`: Join the group with the indicated number.
- `!whereis @name1 ... @namek`: Find out which groups the members listed are in.

#### Once in a group

Once in a group, some other options become useful:

- `!invite @name`: Invite someone to a closed group you are in.
- `!raise-hand` (or `!rh`) Ask for help from the teaching team, one of which will come to the group as soon as possible.
- `!open`: Open the group to allow other students to join.
- `!close`: Close the group so only invited students can join.
- `!leave`: Leave the group.

### Teaching team commands

You have to have one of the following roles: Profesor, Auxilar or Ayudante. Then you will have permissions to see any created group on the server. 

Some of the following commands are only available to Professor or Auxiliar.

#### Category create/delete groups

- `!create-group`: Create new group. Aliases=`!cg` and `!create`
- `!create-many-groups <n>`: Create n new groups. Alias=`!cmg`
- `!delete-all-groups`: Delete all groups.
- `!delete-group <group_num>`: Delete the given group. Aliases=`!dg` or `!delete`
- `!list`: List the members in all groups.

#### Category make groups

- `!move @<name> <group_num>`: Move student to the given group. The `@` is to mention other users or members on the server (and provides autocomplete). If the group is closed, the student needs an invitation beforehand.

- `!make-group @<name_1> ... @<name_n>`\*: Assign the designated students to a open group. If there are no open groups, a new one will be created. The command fails if you include more students than the allowed limit or if you include a member that doesn't exist. Aliases= `!mk` and `!group`

#### Communication

- `!broadcast <msg>`: Send the message to the text channel of each group. (Might get noisy and takes a minute or two.)

#### Respond to help

Students can use `!rh` to ask for help. A call for help will appear in `text-general`. In order for a member of the teaching team to respond, they can add a reaction (an emoticon) to the call for help. They will be added to the group and transfered to their channels. In order to officially leave the group, they can type `!leave` in a chat channel.

Another option is for a member of the teaching team to use `!go`. This is very useful if things get busy. The command goes to the oldest group in a queue of those asking for help. It is important that they are not currently in a group, however (use `!leave` to exit an old group in case of an issue).

A final option is to just use the left menu to navigate to a group's channels and talk to them directly. This is not a recommended option as the group will remain in the queue asking for help.
