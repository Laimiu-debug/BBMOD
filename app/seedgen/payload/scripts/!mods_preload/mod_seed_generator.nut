::SeedGenerator <- {
	ID = "mod_seed_generator",
	Name = "SeedGenerator",
	Version = 1.0,
}

::mods_registerMod(::SeedGenerator.ID, ::SeedGenerator.Version, ::SeedGenerator.Name);
::mods_queue(::SeedGenerator.ID, "", function()
{
	// return;

	::include("seed_generator/function_endless_loop_fixed");
	::include("seed_generator/function_named_attr");
	::include("seed_generator/function_generate_brother");
	::include("seed_generator/function_role_score");
	::include("seed_generator/function_print_info");
	::include("seed_generator/function_generate_settlement");
	::include("seed_generator/function_generate_lair");

	::include("seed_generator/config_common");
	::include("seed_generator/config_map_condition");
	::include("seed_generator/config_role_condition");
	::include("seed_generator/config_lair_condition");

	::include("seed_generator/function_main_loop");

	::include("seed_generator/config_campaign");
	::include("seed_generator/function_auto_start");
});
