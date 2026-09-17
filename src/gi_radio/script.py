"""The complete VideoScript: "The Voice in the Hooch".

One grunt. One year. One radio that would not shut up.
Runtime is computed from word count at theatrical pace plus silent holds.
"""

from __future__ import annotations

from datetime import date

from .schema import (
    CINEMATIC_STYLE,
    ColorGrade,
    EmotionalBeat,
    GradeVariant,
    Protagonist,
    RenderSettings,
    Scene,
    Transition,
    VideoScript,
    VoiceRole,
    VoiceSettings,
    timed,
)

NEGATIVE_PROMPT = (
    "text, watermark, signature, logo, modern clothing, smartphone, digital camera, "
    "cartoon, anime, 3d render, plastic skin, bright cheerful daylight, saturated colors, "
    "gore, blood, wounds, deformed hands, extra limbs, blurry, low resolution"
)


def prompt(subject: str) -> str:
    """Build a ComfyUI positive prompt that always carries the house style."""

    return (
        f"{subject} Vietnam War era 1968, authentic period detail, US Army jungle fatigues, "
        f"no modern objects, no text. {CINEMATIC_STYLE} Painterly brushwork, deep shadow, "
        "film grain, wet surfaces, rim light, shallow depth of field."
    )


B = EmotionalBeat
N = VoiceRole.NARRATOR
H = VoiceRole.HANNAH_RADIO
DAY = GradeVariant.DAY_BRUISED
NIGHT = GradeVariant.NIGHT_RADIO


def scene(
    scene_id: str,
    beat: EmotionalBeat,
    voice: VoiceRole,
    text: str,
    visual_subject: str,
    image_subject: str,
    sfx: list[str],
    *,
    hold: float = 3.0,
    transition: Transition = Transition.CROSSFADE,
    grade: GradeVariant = DAY,
) -> Scene:
    text = text.strip()
    return Scene(
        scene_id=scene_id,
        beat=beat,
        duration_seconds=timed(text, hold_seconds=hold),
        narration_text=text,
        elevenlabs_voice=voice,
        sfx_notes=sfx,
        comfyui_image_prompt=prompt(image_subject),
        visual_subject=visual_subject,
        transition_in=transition,
        grade_variant=grade,
    )


VOICES: dict[VoiceRole, VoiceSettings] = {
    N: VoiceSettings(
        role=N,
        voice_name="Narrator - mature American male, low and tired",
        voice_id_env="ELEVENLABS_NARRATOR_VOICE_ID",
        default_voice_id="pqHfZKP75CvOlQylNhV4",
        model_id="eleven_multilingual_v2",
        stability=0.62,
        similarity_boost=0.80,
        style=0.18,
        use_speaker_boost=True,
        speed=0.88,
        paragraph_break_seconds=1.4,
        performance_notes=(
            "Mature American male, mid-forties to fifties. Low register, dry, tired. "
            "Never pushes. Speaks as if telling it once, late, to a single listener in a dark "
            "room with a radio hissing nearby. Short sentences land and stop. Let paragraph "
            "breaks be real silence. No announcer polish, no documentary lift at the end of "
            "sentences. Quoted GI dialogue stays flat and quiet, not performed."
        ),
    ),
    H: VoiceSettings(
        role=H,
        voice_name="Hannah radio - thin female, careful English, slightly too calm",
        voice_id_env="ELEVENLABS_HANNAH_VOICE_ID",
        default_voice_id="EXAVITQu4vr4xnSDxMaL",
        model_id="eleven_multilingual_v2",
        stability=0.85,
        similarity_boost=0.65,
        style=0.05,
        use_speaker_boost=False,
        speed=0.90,
        paragraph_break_seconds=1.8,
        performance_notes=(
            "Young woman, thin and even, English almost perfect with a schoolroom care in "
            "every consonant. Slightly too calm. Never threatening in tone; the threat is in "
            "the words and the pauses. Reads names like a teacher taking attendance. The "
            "radio band-pass, compression and hiss are added in FFmpeg, not here, so record "
            "her clean and close."
        ),
    ),
}


PROTAGONIST = Protagonist(
    first_name="Danny",
    last_name="Pruitt",
    age_on_arrival=19,
    hometown="Chillicothe, Ohio",
    unit="Delta Company, 3rd Battalion, 22nd Infantry, 25th Infantry Division",
    area_of_operations="Tay Ninh Province, III Corps, near the Cambodian border",
    arrival_date=date(1968, 6, 12),
    deros_date=date(1969, 6, 11),
    writes_home_to=["his mother", "Carol Ann"],
)


COLOR_GRADE = ColorGrade(
    name="Bruised Green / Wet Black / Sick Yellow / Cold Blue",
    description=(
        "One grade for every frame. Shadows crushed into wet blacks with a faint green cast. "
        "Midtones pulled toward bruised olive and mildew green. Highlights leak into a sick, "
        "feverish yellow, never clean white, as if the heat itself were jaundiced. Saturation "
        "held low so red only appears in clay dust and the radio dial. Night and radio scenes "
        "swing the same grade toward a cold blue glow, the only cool light in the film: the "
        "dial, a wristwatch face, a flare. Heavy vignette so every frame feels watched from "
        "inside a bunker."
    ),
    base_filter=(
        "curves=master='0/0 0.25/0.21 0.5/0.48 0.75/0.76 1/0.96'"
        ":red='0/0 0.5/0.49 1/0.95'"
        ":green='0/0.02 0.5/0.53 1/0.99'"
        ":blue='0/0.03 0.5/0.46 1/0.88',"
        "colorbalance=rs=-0.06:gs=0.07:bs=-0.03:rm=0.02:gm=0.05:bm=-0.07:rh=0.08:gh=0.06:bh=-0.14,"
        "eq=contrast=1.08:saturation=0.78:gamma=0.95,"
        "vignette=angle=PI/4.6"
    ),
    night_radio_filter=(
        "curves=master='0/0 0.25/0.18 0.5/0.44 0.75/0.74 1/0.94'"
        ":red='0/0 0.5/0.44 1/0.90'"
        ":green='0/0.01 0.5/0.49 1/0.96'"
        ":blue='0/0.05 0.5/0.55 1/1.0',"
        "colorbalance=rs=-0.10:gs=0.02:bs=0.10:rm=-0.06:gm=0.00:bm=0.10:rh=-0.04:gh=0.02:bh=0.12,"
        "eq=contrast=1.12:saturation=0.70:gamma=0.92,"
        "vignette=angle=PI/4.2"
    ),
)


SCENES: list[Scene] = [
    scene(
        "S01",
        B.COLD_OPEN,
        N,
        """
Before anything else, there is the static.

You are nineteen years old. You are lying on a cot built from ammunition crates, in a country you could not have found on a map twelve months ago. The rain is on the tin. The radio is on the floor, and its dial is the only light for a mile.

Somewhere north of you, a woman is about to say your unit's name.

Not yet.

First, the ordinary part. First, the last night you were ever a boy.
""",
        "Transistor radio on a plywood hooch floor, dial glowing, rain on tin",
        "Close view of a battered transistor radio on a wet plywood floor inside a dark sandbagged hooch, "
        "the amber-blue dial the only light, a boot and the edge of an ammo-crate cot in shadow, "
        "rain streaks on corrugated tin above.",
        ["radio static, slow tuning sweep", "rain on tin roof, steady", "distant single insect"],
        hold=6.0,
        transition=Transition.FADE_BLACK,
        grade=NIGHT,
    ),
    scene(
        "S02",
        B.LAST_ORDINARY_NIGHT,
        N,
        """
Port Columbus, Ohio. June, 1968.

His name is Danny Pruitt. He is from Chillicothe, forty-five miles south, where the paper mill makes the whole town smell like boiled cabbage on a hot day. He has never been on an airplane.

His mother has brought a sandwich wrapped in wax paper. His father is holding his hat with both hands. Carol Ann is standing a little apart, the way you stand at a funeral when you are not sure you are family yet.

Inside his wallet, folded twice, is a sheet of notebook paper. Three hundred and sixty-five small boxes. He drew them last night at the kitchen table.

He has not crossed one off. You do not cross off a day you are still standing in Ohio.
""",
        "Airport glass at night, a family reflected, a boy in uniform with a duffel",
        "A 1968 Midwestern airport terminal at night seen through tall rain-flecked glass, a young soldier "
        "in Army khakis with a duffel bag, his mother holding a paper-wrapped sandwich, a father clutching "
        "a hat with both hands, a young woman standing slightly apart, their reflections doubled in the glass.",
        ["terminal PA murmur, distant", "footsteps on terrazzo", "a paper bag crinkling", "a jet spooling up outside"],
        hold=4.0,
    ),
    scene(
        "S03",
        B.LAST_ORDINARY_NIGHT,
        N,
        """
Oakland. Then a bus in the dark to Travis Air Force Base.

The airplane is a chartered jet, painted a yellow so bright it looks like a mistake. There are stewardesses. There is a hot meal. Somebody's transistor is playing the Rascals. For twenty-two hours it will be possible to believe this is a vacation somebody else planned.

Anchorage. Then the black Pacific. Then an island he cannot name.

He does not sleep. He takes the paper out of his wallet and looks at the first box, and puts it back.

Some of the men on this plane are coming back with him. He does not know which ones, and neither do they.
""",
        "Bright yellow chartered jet under floodlights at Travis AFB, night, soldiers boarding",
        "A brightly painted yellow chartered airliner under harsh sodium floodlights on a military airfield "
        "at night, a long line of young soldiers in khakis climbing the boarding stairs with duffel bags, "
        "wet tarmac reflecting the lights, fog at the edges.",
        ["jet engines idling", "boarding stairs clanging", "faint 1968 pop song from a transistor radio", "wind"],
        hold=4.0,
    ),
    scene(
        "S04",
        B.AIRCRAFT_DOOR_OPENS,
        N,
        """
Bien Hoa. Eight in the morning, and it is already the hottest day of his life.

The door of the aircraft opens, and the heat does not come in. It climbs in. It puts its hand over your mouth. It is wet, and it is alive, and it smells like jet fuel and wood smoke and something rotten and something sweet, and underneath it all, faintly, like a rumor, something burning that should not be burned.

At the bottom of the stairs, a line of men is waiting to get on. They are thin. Their fatigues are the color of dishwater. Their eyes are older than their faces.

One of them looks at Danny's new boots, and says, quietly, almost kindly:

"You'll be sorry."

He is not being cruel. He is being accurate.
""",
        "Airliner door open onto white heat at Bien Hoa, tarmac shimmer, silhouettes waiting below",
        "View from inside an airliner doorway opening onto a blinding, shimmering tropical airfield, "
        "heat haze warping the tarmac, a line of gaunt sun-faded soldiers waiting at the foot of the stairs, "
        "sandbagged revetments and palm trees in a sick yellow light, smoke on the horizon.",
        ["cabin door seal hiss", "jet turbines winding down", "heat shimmer drone", "far-off helicopter rotor"],
        hold=5.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S05",
        B.AIRCRAFT_DOOR_OPENS,
        N,
        """
The bus has wire mesh over the windows. So no one can throw anything in, the driver says, and does not say what.

Long Binh. The Ninetieth Replacement Battalion. Rows of tin roofs, red dust, the smell of diesel burning in cut-down drums behind the latrines. They take your stateside uniform. They give you jungle fatigues that smell of new canvas and mothballs, and boots with drain holes in the sides, and you understand, without anyone saying it, what the holes are for.

Someone hands you a card. Your DEROS. Date Eligible for Return from Overseas. June the eleventh, 1969.

You read it the way a man reads a diagnosis.

Ohio was this morning. By tonight it is a rumor.
""",
        "Army bus with wire mesh over the windows on a red dust road, faces behind the mesh",
        "An olive-drab Army bus with heavy wire mesh over its windows rolling down a red-dust road past tin-roofed "
        "barracks and sandbag walls, young faces pressed to the mesh, a burn barrel smoking behind a latrine, "
        "overcast sky heavy with coming rain.",
        ["bus diesel engine", "gravel under tires", "mesh rattling", "a distant Huey"],
        hold=4.0,
    ),
    scene(
        "S06",
        B.SHORT_TIMER_MATH,
        N,
        """
Here is the first thing you learn in Vietnam. Not how to shoot. How to count.

Everybody counts, and everybody counts backward. A man with two hundred days is a lifer. A man with ninety is getting short. A man with twenty is so short he could sit on a dime and swing his legs. He will tell you so. He will tell you so twice.

You are a cherry. You are an FNG. The old men will not learn your name until you have lasted two weeks, because too many names have already gone home in a bag, and there is only so much room in a man for names.

Danny has three hundred and sixty-three. He has a pen now. He makes his first X on the bus.
""",
        "Helmet cover with a hand-drawn short-timer calendar, ballpoint X marks, a pen",
        "Extreme close-up of a sweat-stained camouflage helmet cover with a hand-drawn grid of small boxes in "
        "ballpoint, only two crossed out, a cheap pen resting on the brim, a young hand with dirty nails, "
        "shallow focus, humid gray light.",
        ["ballpoint on canvas", "bus engine idling", "men's voices low, counting", "a zipper"],
        hold=4.0,
    ),
    scene(
        "S07",
        B.SHORT_TIMER_MATH,
        N,
        """
The C-130 to Tay Ninh smells of hydraulic fluid and a hundred men trying not to be afraid.

Delta Company. Third Battalion, Twenty-Second Infantry. Twenty-Fifth Infantry Division. A base camp under a mountain that stands alone on a flat green plain like something left behind on purpose.

The first man who speaks to him is a private first class from Tupelo, Mississippi, named Roy Lee Macon. He has been here seven months. He talks slow, and he does not smile, and he says:

"Don't walk where the grass is bent. Don't drink from the paddy. Don't fall in love with anybody in-country." He pauses. "Including me."

Then he shows Danny how to tape the sling on his rifle so it will not rattle in the dark.

That is how you know he has decided to learn your name.
""",
        "C-130 rear ramp lowering onto red dust, a lone dark mountain on a flat green plain beyond",
        "The lowered rear ramp of a C-130 transport framing a red-dust airstrip and, far off, a single dark "
        "mountain rising alone from a flat green plain under a bruised sky, soldiers on web seats in the "
        "shadowed cargo bay, rotor dust drifting.",
        ["C-130 turboprops", "hydraulic ramp whine", "boots on aluminum deck", "wind across the strip"],
        hold=4.0,
    ),
    scene(
        "S08",
        B.RADIO_INTERLUDE,
        H,
        """
Good evening, GI Joe. This is Thu Hương, speaking to you from Hanoi.

How are you tonight?

I am told there are new men with the Twenty-Fifth Division at Tay Ninh. Welcome to Vietnam, boys. You have a long year ahead. Three hundred and sixty-five days. Perhaps fewer.

We have been waiting for you.
""",
        "Hooch radio in the dark, dial glow throwing cold blue light across a wet plywood floor",
        "A small transistor radio on an upturned ammunition crate inside a dark hooch, its dial casting a cold "
        "blue glow across wet plywood, mosquito netting and a hanging poncho in shadow, one bare foot at the "
        "edge of the light.",
        ["radio static bed, AM warble", "rain on tin, light", "a cot creaking", "mosquito whine"],
        hold=5.0,
        transition=Transition.RADIO_DISSOLVE,
        grade=NIGHT,
    ),
    scene(
        "S09",
        B.RADIO_INTERLUDE,
        N,
        """
The first time you hear her, somebody laughs.

Somebody else says, "Turn her off," and nobody does.

She is on three times a day. Her English is almost perfect. Not quite. There is a little too much care in it, like a teacher reading a story to children she does not like. That is what makes it worse. If she screamed, you could hate her. She never screams.

Macon lies on his cot with his eyes closed and says, "She's just talking."

He does not turn her off either.
""",
        "Men in a hooch at night, one laughing, one staring at the radio, one lying still",
        "Interior of a sandbagged hooch at night lit only by a candle and a radio dial, three young soldiers "
        "on cots, one laughing with his head back, one staring hard at the radio, one lying with eyes closed "
        "and an arm across his chest, cigarette smoke hanging.",
        ["radio voice bleeding through static, muffled", "a short laugh", "cot springs", "rain"],
        hold=4.0,
        grade=NIGHT,
    ),
    scene(
        "S10",
        B.LAND_AS_ENEMY,
        N,
        """
You learn the rain first. Not weather. A weight.

The monsoon comes in the afternoon like it has been waiting ten thousand years for you specifically. It does not fall. It arrives. It fills your collar and your boots and your ears. It gets into the C-rations. It gets into your mouth when you talk, so you stop talking. It gets into the letters, so the ink runs and you read the shape of the words instead of the words.

At night you lie in a hole with a poncho over you, and the water comes up from below, and you sleep half-submerged, like something that has not decided whether to be a man or a fish.

Nobody tells you the rain will be the enemy you remember. They tell you about the other one.
""",
        "Monsoon over a flooded paddy, grunts hunched under ponchos, rain in sheets",
        "A column of soldiers hunched under dripping ponchos wading a flooded rice paddy in a monsoon downpour, "
        "rain falling in gray sheets, treeline lost in mist, a soaked letter clutched in one fist, "
        "the sky the color of wet slate.",
        ["monsoon downpour, heavy", "boots sucking in mud", "water dripping off poncho brim", "thunder far off"],
        hold=5.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S11",
        B.LAND_AS_ENEMY,
        N,
        """
When the rain stops, the heat comes back like it is angry you got a break.

Your clothes never dry. Not once. Not in a year. Your skin under them goes white and soft and starts to come off in strips. The medic calls it jungle rot and gives you a powder that does nothing. Leeches come up out of the paddy and fasten on where your belt sits, and you burn them off with a cigarette, and the little holes bleed for an hour.

There are insects here you do not have names for. There are plants that cut. There is a country that seems, in its entirety, in its water and its air and its dirt, to want you dead.

You are nineteen. You take it personally. That is a mistake, and you cannot stop making it.
""",
        "Wet boots pulled off, pale ruined feet, a medic's flashlight, a leech on a calf",
        "Close view of a soldier's bare pale waterlogged feet beside unlaced jungle boots on muddy ground, "
        "a medic's flashlight beam in the humid dusk, a leech on a calf, steam rising off wet fatigues, "
        "sick yellow-green light through the canopy.",
        ["insects, dense chorus", "wet cloth peeling", "a lighter clicking", "dripping canopy"],
        hold=4.0,
    ),
    scene(
        "S12",
        B.MAIL_CALL,
        N,
        """
Mail comes on the helicopter. The helicopter comes when it comes.

Some days you hear the rotor and stand up like a dog. Some days you hear it and it turns away, and you sit down, and nobody says anything about it.

But when the red bag lands. When the sergeant reads the names. Then a letter is a piece of sunlight passed down into a dungeon on a string.

Carol Ann writes on blue paper. His mother writes on lined paper from the same pad she uses for grocery lists. The pages arrive soaked. He dries them on his helmet in the sun and reads them four times, and then he reads them to Macon, who reads him Darlene's letters from Tupelo in exchange, slow, like scripture.

A care package. Cookies powdered to crumbs. Kool-Aid. A can of peaches he does not open for eleven days, because opening it means it is gone.
""",
        "A Huey settling onto a wet LZ, a red mail sack thrown out, men running bent over",
        "A UH-1 Huey helicopter settling onto a muddy landing zone in blowing rain, a red canvas mail sack "
        "tumbling from the open door, soldiers running bent double toward it through flattened grass, "
        "rotor wash flinging water, low gray sky.",
        ["Huey rotor approaching then flaring", "rotor wash on grass", "men shouting names", "a paper envelope tearing"],
        hold=5.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S13",
        B.MAIL_CALL,
        N,
        """
Then the other kind of letter.

Ferris, from Bakersfield, gets his on a Tuesday. It is one page. He reads it three times, and folds it, and puts it in the band of his helmet, where the cigarettes go. He does not say anything. Nobody asks.

That is the rule. You are allowed to be destroyed here. You are not allowed to be watched while it happens.

Danny looks at the blue envelope in his own hand, and for a second he is afraid to open it. Then he does. It is only about her sister's wedding.

He is so relieved he has to sit down. He is ashamed of that for a long time.
""",
        "A soldier alone on an ammo crate with a one-page letter, others looking away",
        "A young soldier sitting alone on an ammunition crate holding a single page of a letter, helmet in his "
        "lap with cigarettes in the band, other soldiers in the background deliberately looking away, "
        "sandbags and a dripping poncho shelter, flat overcast light.",
        ["paper unfolding, slowly", "distant generator", "rain easing to drips", "silence held"],
        hold=5.0,
    ),
    scene(
        "S14",
        B.RADIO_AFTER_DARK,
        H,
        """
GI, it is late. Are you thinking about your girl tonight?

She is thinking about you, too. Or she was. It has been a long time. There are boys at home who did not have to go. She is young. You cannot blame her.

Here is a song you know. It is called "We Gotta Get Out of This Place."

Listen to the words, GI. Then look at your watch. Your minutes are ticking.
""",
        "Radio dial close-up, cold blue glow, rain streaking a bunker doorway behind",
        "Extreme close-up of a glowing radio dial with its needle on a frequency, cold blue light on a scarred "
        "plastic face, a bunker doorway behind streaked with night rain, sandbags black with water.",
        ["AM radio static, slow fade", "rain through a doorway", "a wristwatch ticking, close", "a song starting tinny then cut"],
        hold=6.0,
        transition=Transition.RADIO_DISSOLVE,
        grade=NIGHT,
    ),
    scene(
        "S15",
        B.RADIO_AFTER_DARK,
        N,
        """
Her real name is Trịnh Thị Ngọ. The men call her Hanoi Hannah. She never calls herself that.

She reads from Stars and Stripes. She knows which battalions moved where, sometimes before the battalions do. She plays the Animals and Pete Seeger and "Where Have All the Flowers Gone," and she waits while it plays, and the waiting is the point.

She says the war is lost. She says the girl is not waiting. Most nights, most men hoot at her.

Here is what nobody says out loud. The cruelty is not that she is believed. Mostly she is not.

The cruelty is that at eleven at night, in a bunker, with the rain on the tin, she sounds like she is sitting right there in the dark with you. And she has all the time in the world. And you do not.
""",
        "Silhouetted men around a radio in a bunker, one candle, rain beyond the firing slit",
        "Silhouettes of four soldiers gathered around a small radio inside a sandbagged bunker, a single candle "
        "and the radio dial the only light, rain visible through the firing slit, cold blue glow on wet faces, "
        "deep shadow everywhere else.",
        ["rain on tin, steady", "radio hiss under voice", "a folk song, faint, from the radio", "candle guttering"],
        hold=6.0,
        grade=NIGHT,
    ),
    scene(
        "S16",
        B.SEARCH_AND_DESTROY,
        N,
        """
They call it search and destroy. Nobody in Delta Company calls it anything. They call it going out.

Danny walks point for the first time in September. Point means you are the first thing the country meets. You watch the grass. You watch for the wire you will not see. You learn that a village that waves at you in the daylight is a village that watches you at night, and you do not know, you cannot know, which face is which.

Free-fire zone. That means anything. That means the trees. That means a water buffalo. That means a man running, who might be running because men with rifles are coming, which is a good reason.

There is a Zippo, and there is thatch, and it goes up faster than you thought a home could.
""",
        "Point man alone on a paddy dike at dawn, village treeline ahead, thatch smoke rising",
        "A lone point man walking a narrow paddy dike at gray dawn, rifle low, a village of thatched roofs "
        "in the treeline ahead with a thin column of smoke rising, mist on the water, the rest of the column "
        "far behind him, everything the color of mildew.",
        ["boots on wet earth, slow", "insects", "a dog barking far off", "a Zippo lid, then flame"],
        hold=5.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S17",
        B.SEARCH_AND_DESTROY,
        N,
        """
After a contact there is a quiet that is not like any other quiet.

Nobody talks about what just happened. Somebody counts. That is the scoreboard. That is the only scoreboard. A lieutenant writes a number in a notebook, and the number goes up the radio, and somewhere somebody adds it to another number.

You clean your rifle. Macon hums something with no tune. Ferris looks at his hands like they belong to a man he met once.

You did not see what you did. You will find, later, that this is how you know you did it.

That night you make an X on your helmet. It is the same size as all the others.
""",
        "Men sitting silent on a paddy dike after a contact, smoke drifting, rifles across knees",
        "Soldiers sitting spread out along a paddy dike in the aftermath of a firefight, rifles across their "
        "knees, faces blank, smoke drifting low over the water, spent brass in the mud, a burned treeline "
        "behind them, no one speaking.",
        ["ringing silence, high tone", "smoke crackle far off", "a cleaning rod in a barrel", "a radio handset squelch"],
        hold=6.0,
    ),
    scene(
        "S18",
        B.SHORT_TIMER_MATH,
        N,
        """
October. Day one hundred and twelve.

The paper in his wallet fell apart in August. Now the calendar is on his helmet cover, in ballpoint, in rows. Half of the boxes have an X in them.

Half is the worst place to be. Behind you there is enough to know what this costs. Ahead of you there is enough to kill you twice.

He writes to Carol Ann that things are quiet. He writes to his mother that the food is fine. He tells Macon the truth, and Macon says, "Yep," which is the whole of what there is to say.
""",
        "Helmet calendar half crossed out, bruised green light, a boy's face under the brim",
        "Close-up of a helmet cover calendar with half its boxes crossed out in ballpoint, the brim shadowing "
        "a nineteen-year-old face gone hard, bruised green jungle light, a canteen cup steaming beside him.",
        ["pen on canvas", "canteen cup on a stove", "insects at dusk", "a page turning"],
        hold=4.0,
    ),
    scene(
        "S19",
        B.NAME_ON_THE_RADIO,
        N,
        """
November. Somewhere near the Cambodian border, on a night with no name.

You do not see it. You hear it, and then there is the quiet, and then Doc is walking back with his hands empty.

In the morning they lay out Macon's gear on a poncho liner. The rifle. The canteen. The little Bible his mother sent that he never opened. And a letter, addressed in his slow square hand, to Miss Darlene Coates, Tupelo, Mississippi. It is in a plastic bag. He carried it against his chest.

The letter is dry.

That is how you know something is wrong. In this country, nothing is dry. The only dry thing here is something a man protected with his whole body.

The platoon sergeant fills out a form. It has a box for a date. He fills it in.
""",
        "Gear laid out on a poncho liner in the mud, a letter in a plastic bag on top, boots around it",
        "A soldier's belongings laid out on a camouflage poncho liner in the mud at dawn, a rifle, a canteen, a "
        "small Bible, and on top a sealed letter inside a clear plastic bag, dry, surrounded by the muddy boots "
        "of men standing in a silent circle.",
        ["dawn insects", "plastic bag crinkling", "a pen on a clipboard", "silence, long"],
        hold=7.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S20",
        B.NAME_ON_THE_RADIO,
        H,
        """
And now, GI, the names of your comrades who will not be going home this week.

Specialist Fourth Class Lawrence Petrakis. Youngstown, Ohio.

Sergeant Dale Ambrose. Bakersfield, California.

Private First Class Roy Lee Macon. Tupelo, Mississippi.

Their families have been informed. Their names were printed in your own newspaper, GI. I only read them to you.

Has yours been printed yet?
""",
        "Radio in the dark, the men's faces half lit blue, nobody moving",
        "A radio on the floor of a dark bunker throwing cold blue light upward onto the still faces of "
        "young soldiers who have stopped moving, a hand frozen above the dial, rain on sandbags outside, "
        "everything else swallowed in black.",
        ["radio static, thin", "distant 105mm battery, slow rhythm", "rain", "no other sound"],
        hold=7.0,
        transition=Transition.RADIO_DISSOLVE,
        grade=NIGHT,
    ),
    scene(
        "S21",
        B.NAME_ON_THE_RADIO,
        N,
        """
He is in the bunker when she says it.

Roy Lee Macon. Tupelo. In her mouth, in her careful schoolroom English, like she is reading the name of a town she plans to visit.

Nobody hoots. Ferris reaches over and turns the dial, and the dial hisses, and she is gone, and it does not help, because she has already said it.

Somewhere in Mississippi, a car is pulling up to a house. A man in a Class A uniform is straightening his tie in the rearview mirror. He has done this before. He will do it again.

And the last letter Darlene wrote is already on its way back to her, with an Army form clipped to the front, saying he died on a date she still thought he was reading.

There is no wall yet with his name on it. There is only a woman in Hanoi who owns the ending, and a boy in Tay Ninh who has to hear her read it.
""",
        "A lone GI standing outside the bunker in the rain, radio glow behind him in the doorway",
        "A single young soldier standing bareheaded in night rain outside a sandbagged bunker, his back to the "
        "cold blue radio glow spilling from the doorway, shoulders down, the wire and a flare-lit sky beyond, "
        "water running off his face.",
        ["rain, close", "radio hiss cut to silence", "a flare popping far off", "breath"],
        hold=7.0,
        grade=NIGHT,
    ),
    scene(
        "S22",
        B.HOLIDAY_IN_THE_RAIN,
        N,
        """
Thanksgiving. The twenty-eighth of November, 1968.

There is turkey. They fly it out in green insulated cans, and by the time it lands the gravy has a skin on it, and you eat it standing up in the rain with your rifle across your back.

There are no bells. There is a battery of one-oh-fives on the firebase, and they fire all afternoon, and the sound goes through your chest like a door slamming in the next room.

His mother's care package came a month early. In it is a plastic Christmas tree, eight inches tall, with the ornaments already glued on. He sets it on the sandbags. It rains on it.

He writes home: "I am thankful to be here with the guys."

He looks at the sentence for a long time. He does not believe it. He does not cross it out.
""",
        "Firebase at dusk in rain, a tiny plastic Christmas tree on sandbags, a howitzer beyond",
        "A muddy firebase at dusk in steady rain, an eight-inch plastic Christmas tree standing on a sandbag "
        "wall, a soldier eating from a mess tray with a rifle slung across his back, a 105mm howitzer under a "
        "tarp firing in the background, muzzle flash lighting the rain.",
        ["105mm howitzer, repeated, chest-deep", "rain on sandbags", "a mess tray scraping", "a pen on damp paper"],
        hold=6.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S23",
        B.HOLIDAY_IN_THE_RAIN,
        N,
        """
Christmas is dry. The rain quits, the way it does here, all at once, like an argument ending. The mud turns to a red dust that gets in your teeth.

There is a truce. It is on paper. At midnight somebody fires flares, and they hang over the wire on their little parachutes like the wrong stars.

On the radio she plays "I'll Be Home for Christmas." She lets the whole song play.

Then she says: "If only in your dreams, GI."

Ferris says, "Merry Christmas, Hannah." He says it to the radio. He means it, kind of. That is the strangest part.
""",
        "Parachute flares hanging over the wire at midnight, red tracers far off, dust",
        "Illumination flares drifting under small parachutes above concertina wire at midnight, their harsh "
        "light on a dusty perimeter and a soldier's upturned face, faint red tracers on the far horizon, "
        "a radio glowing at his feet.",
        ["flare pop and hiss", "parachute flare swinging", "distant small arms, sporadic", "radio playing a Christmas song, tinny"],
        hold=5.0,
        grade=NIGHT,
    ),
    scene(
        "S24",
        B.SEARCH_AND_DESTROY,
        N,
        """
February. The rockets come into the base camp at night, and the new year has a new set of cherries who do not know his name yet, and he does not learn theirs.

He is not in the battles you have heard of. He is near some of them. That is what the war is for most men: near. Near enough to hear it. Near enough to carry stretchers to the pad afterward. Near enough that the numbers on the radio are numbers he could put faces to, if he let himself.

He does not let himself. He has one hundred and nine days.

He has stopped reading Carol Ann's letters to anyone. There is less in them. It is not her fault. There is less in his.
""",
        "Base camp at dawn after a rocket attack, a burning fuel dump on the horizon, men carrying a stretcher",
        "A sprawling base camp at first light after a rocket attack, black smoke from a burning fuel dump on "
        "the horizon, two soldiers carrying a covered stretcher toward a helicopter pad, red dust hanging, "
        "the lone mountain dim in the haze.",
        ["Huey rotor idling on the pad", "fire roaring far off", "boots on hard dust", "a whistle blown once"],
        hold=5.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S25",
        B.RADIO_AFTER_DARK,
        H,
        """
How are you, GI Joe? Still there?

Your President speaks of peace in Paris. The men who sent you have already decided how this ends. They are only waiting for the paperwork.

You are not waiting for paperwork. You are waiting for the next patrol.

Look at your watch, GI. Look at the second hand. That is the sound of your year. Tick. Tick.

I will be here tomorrow. Will you?
""",
        "A wristwatch on a wrist in cold blue radio light, second hand mid-sweep",
        "Extreme close-up of a scratched military wristwatch on a thin sunburned wrist, lit only by the cold "
        "blue glow of a radio dial just out of frame, the second hand caught mid-sweep, dark bunker beyond.",
        ["wristwatch ticking, very close", "AM static", "a slow breath", "rain, distant"],
        hold=6.0,
        transition=Transition.RADIO_DISSOLVE,
        grade=NIGHT,
    ),
    scene(
        "S26",
        B.SHORT_AND_SHORTER,
        N,
        """
May. Day three hundred and forty.

He is short. He is so short he could sit on a dime and swing his legs. He says it. He says it twice, and hears Macon in it, and stops saying it.

Here is what nobody tells you about being short. The last weeks are the most dangerous. Not because the country changes. Because you do. You start to believe in June. Hope makes you sloppy. Hope makes you look up when you should be looking at the grass.

The sergeant takes him off point. He argues. He loses. He is grateful, and ashamed of being grateful, which is by now a feeling he knows the way he knows his own boots.

The freedom bird. Every man in Vietnam talks about it like a myth. Like something that might still not be real when you get to the airfield.
""",
        "Helmet calendar nearly full, SHORT written across the cover, jungle edge behind",
        "A helmet with a nearly complete grid of crossed-out boxes and the word SHORT inked across the cover, "
        "resting on a rucksack at the edge of dense jungle, humid haze, a young soldier's hand reaching for it, "
        "sick yellow afternoon light.",
        ["insects, heavy", "a helmet set down on a ruck", "distant Huey", "boots on a trail, slow"],
        hold=5.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S27",
        B.SHORT_AND_SHORTER,
        N,
        """
June the ninth. A truck to Cu Chi. A C-130 to Bien Hoa. Long Binh again, the same tin roofs, coming at it from the other side.

He gives his radio to a cherry who does not know what he is being handed.

At Long Binh they take the jungle fatigues. They give him khakis that do not fit. There is one box left on the calendar. He does not X it. You do not cross off a day you are still standing in Vietnam.

The last night he cannot sleep. He lies awake and listens for her, out of habit, and there is no radio now, and there is only the generators and the rain.

It is the first night in a year he does not know what she said.
""",
        "A GI in the back of a truck on a red road, duffel between his knees, looking back at the lone mountain",
        "A young soldier riding in the open back of a deuce-and-a-half truck on a red dirt road, duffel between "
        "his knees, looking back over his shoulder at a lone dark mountain receding on the plain, dust "
        "boiling behind the convoy, storm light.",
        ["truck engine and gears", "gravel and dust", "convoy radio chatter, faint", "generators at night, later"],
        hold=6.0,
    ),
    scene(
        "S28",
        B.COMING_HOME,
        N,
        """
The door of the aircraft opens the other way.

Travis Air Force Base. Four in the morning. Fog. Fifty-eight degrees, and the cold goes into him like a knife, and he is so happy about it he almost cries, and then he does not, because he has forgotten how that is done.

There is nobody at the gate. Not for him, not for anybody. A bus to San Francisco. In the airport bathroom he changes into the shirt his mother sent, and it hangs on him like it was bought for a different boy, and in a way it was.

A man in the terminal looks at his khakis and looks away. That is all. That is the whole parade.
""",
        "Airliner door open onto gray fog at Travis, thin men in rumpled khakis coming down the stairs",
        "An airliner door opening onto cold gray predawn fog on a military airfield, thin young men in rumpled "
        "khakis descending the stairs with duffel bags, breath visible, floodlights haloed in mist, no one waiting "
        "on the empty tarmac.",
        ["cabin door hiss", "cold wind", "footsteps on wet stairs", "fog horn, very distant"],
        hold=6.0,
        transition=Transition.FADE_BLACK,
    ),
    scene(
        "S29",
        B.COMING_HOME,
        N,
        """
Port Columbus. His father is holding his hat with both hands. His mother is smaller than she was. Carol Ann is there. She smells like a house. She kisses him, and pulls back a little, and does not know why, and he does.

It is the smell. It is in his skin. Jet fuel and wood smoke and wet canvas and something rotten and something sweet. Nobody in Ohio can smell it. He will smell it for years.

He sleeps on the floor of his room the first night, because the bed is too soft and too high and too far from the ground.

At three in the morning he turns on the transistor and moves the dial slowly across the whole band, all the way, and back.

Cincinnati. Static. Columbus. Static. Nobody knows his unit's name.
""",
        "A boy's bedroom in Ohio at 3 a.m., one lamp, a transistor radio on the floor beside him",
        "A small-town Ohio bedroom at three in the morning, a young man sitting on the floor with his back "
        "against a too-soft bed, one dim lamp, a transistor radio beside him with its dial glowing faint blue, "
        "a duffel bag unopened in the corner, curtains still.",
        ["radio dial sweeping, station fragments and static", "a house settling", "a clock in another room", "no insects"],
        hold=6.0,
        grade=NIGHT,
    ),
    scene(
        "S30",
        B.COMING_HOME,
        N,
        """
In August a letter comes to Chillicothe with a Tupelo postmark.

She writes small. She says they sent her letter back with a form on it. She says the form had a date. She says she had been writing to him for nine days after that date, and she wants to know, from somebody who was there, whether he got the last one. Whether he read it.

Danny sits at the kitchen table with a pen.

He does not know if Macon got her last one. He knows what Macon was carrying when he went. He knows it was dry.

He does not know how to write that yet.

On the dresser, the radio is off. It has been off for two months. In the closet, on a helmet cover, three hundred and sixty-five boxes, every one of them crossed out.

The calendar is finished.

The boy is not.
""",
        "A kitchen table at night: a returned envelope with an Army form, a finished helmet calendar, a dark radio",
        "A worn kitchen table under a single hanging lamp at night, an opened envelope with a Mississippi "
        "postmark and a folded Army form beside it, a helmet cover with every box crossed out, a dark silent "
        "transistor radio, a pen laid down on blank paper.",
        ["a clock ticking", "paper set down", "a lamp hum", "then nothing"],
        hold=10.0,
        transition=Transition.FADE_BLACK,
        grade=NIGHT,
    ),
]


SCRIPT = VideoScript(
    title="The Voice in the Hooch",
    slug="the-voice-in-the-hooch",
    logline=(
        "One American kid, one year in Tay Ninh, and a woman in Hanoi who says his friend's "
        "name on the radio as if she already owns the ending."
    ),
    protagonist=PROTAGONIST,
    voices=VOICES,
    scenes=SCENES,
    color_grade=COLOR_GRADE,
    render=RenderSettings(),
)


def get_script() -> VideoScript:
    return SCRIPT
